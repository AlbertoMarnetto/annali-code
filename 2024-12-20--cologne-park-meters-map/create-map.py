#! env python3

from collections import namedtuple
import csv
from io import BytesIO
from math import sin, cos, pi
from PIL import Image, ImageDraw, ImageFont
import re
import requests
from sys import argv

Coords = namedtuple('Coords', ['lat', 'lon'])

class GeomFactors:
    def __init__(self, map_global_center, zoom):
        # Sources:
        # * http://gis.stackexchange.com/a/127949/93220 
        # * https://docs.microsoft.com/en-us/bingmaps/articles/understanding-scale-and-resolution
        # The formula works across GMaps, OSM and Bing
        # For Bing Maps, `zoom` must apparently be replaced by `zoom - 1`, even if this conflicts
        # with the docs
        self.meter_per_pixel = 1. / 2 * 156543.03392 * cos(map_global_center.lat * pi / 180) / (2**(zoom))
        self.meter_per_deg_northing = 6378137. * 2 * pi / 360
        self.meter_per_deg_easting = 6378137. * 2 * pi / 360 * cos(map_global_center.lat * pi / 180)
        self.deg_per_pixel_northing = self.meter_per_pixel / self.meter_per_deg_northing
        self.deg_per_pixel_easting = self.meter_per_pixel / self.meter_per_deg_easting



def load_maps(api_key, map_global_center, zoom):
    '''Loads from file or downloads from Bing the maps around the given center

    Caches the maps into files, and returns them as array of PIL.Image
    '''
    # Bing max size
    map_pixel_size = [2200, 1800]

    gf = GeomFactors(map_global_center, zoom)
    map_deg_width = map_pixel_size[0] * gf.deg_per_pixel_easting 
    map_deg_height = map_pixel_size[1] * gf.deg_per_pixel_northing

    # Maps:
    # 6 7 8
    # 3 4 5
    # 0 1 2

    result = []
    for x in (-1, 0, 1) :
        for y in (-1, 0, 1) :
            map_filename = f'map_{x + 1}_{y + 1}.jpg'
            try:
                image = Image.open(map_filename)
            except FileNotFoundError:
                map_center = Coords(
                    map_global_center.lat + y * map_deg_height,
                    map_global_center.lon + x * map_deg_width)
                #static_map_url = f'https://dev.virtualearth.net/REST/v1/Imagery/Map/Road/{map_center.lat},{map_center.lon}/{zoom}?mapSize={map_pixel_size[0]},{map_pixel_size[1]}&key={api_key}'
                static_map_url = f'https://maps.geoapify.com/v1/staticmap?style=osm-bright&width={map_pixel_size[0]}&height={map_pixel_size[1]}&center=lonlat:{map_center.lon},{map_center.lat}&zoom={zoom}&apiKey={api_key}'
                print(f'Downloading URL {static_map_url}')
                response = requests.get(static_map_url)
                if response.status_code != 200:
                    raise Exception(f'Failed to download image. Status code: {response.status_code}')
                image = Image.open(BytesIO(response.content))
                image.save(map_filename)

            image_clone = image.copy()
            #result[x_index + 1][y_index + 1] = image_clone
            result.append(image_clone)

    return result

def create_bigmap(api_key, map_global_center, zoom):
    '''
    Combines nine smaller maps in a 3x3 big map. 

    Caches the map in a file
    '''
    bigmap_filename = f'bigmap.jpg'
    try:
        bigmap = Image.open(bigmap_filename)
    except:
        maps = load_maps(api_key, map_global_center, zoom)
        map_pixel_size = maps[0].size 
        bigmap_pixel_size = [ d * 3 for d in map_pixel_size ]

        bigmap = Image.new('RGB', bigmap_pixel_size)

        for x in [0, 1, 2]:
            for y in [0, 1, 2] :
                bigmap.paste(maps[x * 3 + y], (x * map_pixel_size[0], (2 - y) * map_pixel_size[1]))
        bigmap.save(bigmap_filename)
    return bigmap

Parkautomat = namedtuple('Parkautomat', ['activity_times', 'price', 'x', 'y'])
def parkautomat_generator(bigmap_size):
    '''
    Generator reading one line of the Parkscheinautomaten list of Cologne
    '''
    with open('psa_offene_daten_2023.csv', mode='r', newline='', encoding='Windows-1252') as file:
        csv_reader = csv.reader(file, delimiter=';')
        next(csv_reader) # Skip the header
        for row in csv_reader:
            row_tuple = tuple(row)
            activity_times = row_tuple[7]
            price = row_tuple[8]

            try:
                row_lat_string = row_tuple[12]
                row_lat = float(row_lat_string.replace(',', '.'))
                row_lon_string = row_tuple[13]
                row_lon = float(row_lon_string.replace(',', '.'))
            except ValueError:
                continue

            parkautomat_coords = Coords(row_lat, row_lon)
            gf = GeomFactors(map_global_center, zoom)
            parkautomat_delta_coords = Coords(
                    parkautomat_coords.lat - map_global_center.lat,
                    parkautomat_coords.lon - map_global_center.lon
                    )
            parkautomat_x = (bigmap_size[0] / 2) + parkautomat_delta_coords.lon / gf.deg_per_pixel_easting
            parkautomat_y = (bigmap_size[1] / 2) - parkautomat_delta_coords.lat / gf.deg_per_pixel_northing

            yield Parkautomat(activity_times, price, parkautomat_x, parkautomat_y)

class GraphicConstants:
    color_all_week_long = 'black'
    color_late_sats = '#BB00BB'
    color_afternoon_sats = 'red'
    color_morning_sats = '#f79f00'
    color_no_weekends = 'blue'

def create_bigmap_with_park_meters(api_key, map_global_center, zoom):
    annotated_bigmap_filename = 'bigmap-with-park-meters.jpg'
    only_parkmeters_filename = 'only-park-meters.jpg'
    try:
        bigmap = Image.open(annotated_bigmap_filename)
        only_parkmeters = Image.open(only_parkmeters_filename)
    except:
        bigmap = create_bigmap(api_key, map_global_center, zoom)
        draw = ImageDraw.Draw(bigmap)

        only_parkmeters = Image.new('RGB', bigmap.size)
        draw_only_parkmeters = ImageDraw.Draw(only_parkmeters)

        for parkautomat in parkautomat_generator(bigmap.size):
            # Define the coordinates for the marker
            marker_coords = (parkautomat.x, parkautomat.y)

            is_early_saturday = bool(re.search(r'Sa ..:..[ ]?- 1[0-4]:00', parkautomat.activity_times))
            is_evening_saturday = bool(re.search(r'Sa ..:.. - (1[5-9])|(20)|(21):00', parkautomat.activity_times))
            is_other_saturday = 'Sa' in parkautomat.activity_times and not is_evening_saturday and not is_early_saturday

            fill_color = (
                     GraphicConstants.color_all_week_long if 'So' in parkautomat.activity_times
                else GraphicConstants.color_late_sats if is_other_saturday
                else GraphicConstants.color_afternoon_sats if is_evening_saturday
                else GraphicConstants.color_morning_sats if is_early_saturday
                else GraphicConstants.color_no_weekends)
                #else '#f7a900')

            draw_method = draw.ellipse if '0,50' in parkautomat.price else draw.rectangle
            marker_size = 8 if '0,50' in parkautomat.price else 10

            outline_color = "black" if fill_color == GraphicConstants.color_morning_sats else fill_color
            draw_method((marker_coords[0] - marker_size, marker_coords[1] - marker_size,
                         marker_coords[0] + marker_size, marker_coords[1] + marker_size),
                         fill=fill_color, outline=outline_color, width=1)
            draw_only_parkmeters.rectangle(
                    (marker_coords[0] - marker_size, marker_coords[1] - marker_size,
                    marker_coords[0] + marker_size, marker_coords[1] + marker_size),
                    fill='white', outline='white', width=1)

        bigmap.save(annotated_bigmap_filename)
        only_parkmeters.save(only_parkmeters_filename)
    return bigmap

if __name__ == '__main__':
    api_key = argv[1] if len(argv) > 1 else ''
    map_global_center = Coords(50.941, 6.953225210305147)
    zoom = 15

    bigmap = create_bigmap_with_park_meters(api_key, map_global_center, zoom)
    draw = ImageDraw.Draw(bigmap)

    font = ImageFont.truetype('ABeeZee-Regular.ttf', size=50)

    legend_x = 5480
    legend_y = 3750
    legend_w = 1100
    legend_h = 1620
    draw.rectangle([legend_x, legend_y, legend_x + legend_w, legend_y + legend_h], fill='white', outline='black', width=5)

    text_coords = [legend_x + 60, legend_y + 40]
    title = """Parking Meters in Cologne
Parkautomaten in Köln
"""
    title_font = ImageFont.truetype('ABeeZee-Regular.ttf', size=80)
    draw.multiline_text(text_coords, title, fill='black', font=title_font, align='center')

    legend_items = [
        (2, 'grey', draw.rectangle, 10, '4 € / h', None),
        (3, 'grey', draw.ellipse, 8, '2 € / h', None),
        (5, GraphicConstants.color_no_weekends, draw.rectangle, 10, 'Free on weekends', 'Kostenlos am Wochenende'),
        (7, GraphicConstants.color_morning_sats, draw.rectangle, 10, 'Free on Sat. after 14 and Sun.', 'Kostenlos am Sa. ab 14 Uhr und So.'),
        (9, GraphicConstants.color_afternoon_sats, draw.rectangle, 10, 'Free on Sat. after 21 and Sun.', 'Kostenlos am Sa. ab 21 Uhr und So.'),
        (11, GraphicConstants.color_late_sats, draw.rectangle, 10, 'Free on Sunday', 'Kostenlos am Sonntag'),
        (13, GraphicConstants.color_all_week_long, draw.rectangle, 10, 'Paid parking all week round', 'Kostenpflichtig rund um die Woche'),
    ]

    for line_no, fill_color, draw_method, marker_size, legend, legend_de in legend_items:
        marker_size *= 3
        marker_coords = [ legend_x + 80, legend_y + 200 + line_no * 80]
        draw_method((marker_coords[0] - marker_size, marker_coords[1] - marker_size,
                      marker_coords[0] + marker_size, marker_coords[1] + marker_size),
                     fill=fill_color, outline=fill_color)

        if legend_de is None:
            text_coords = [marker_coords[0] + 60, marker_coords[1]]
            draw.text(text_coords, legend, fill='black', font=font, anchor='lm')
        else:
            text_coords = [marker_coords[0] + 60, marker_coords[1] - 30]
            draw.text(text_coords, legend, fill='black', font=font, anchor='lm')
            text_coords = [marker_coords[0] + 60, marker_coords[1] + 30]
            draw.text(text_coords, legend_de, fill='black', font=font, anchor='lm')

    text_coords = [marker_coords[0] - marker_size, marker_coords[1] + 90] 
    closing = """
Map data from OpenStreetMap
Powered by Geoapify
© Alberto Marnetto, 2024 (CC-BY-SA-2.0)
marnetto.net
"""
    draw.multiline_text(text_coords, closing, fill='#555555', font=font)
    bigmap.save("final.jpg")
