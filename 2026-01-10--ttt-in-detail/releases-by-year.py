import re
from collections import Counter
import matplotlib.pyplot as plt
from matplotlib import gridspec
import matplotlib as mpl

mpl.rcParams['font.family'] = 'ABeeZee'
mpl.rcParams['font.size'] = 14

# --- Step 1: Read SQL dump and extract years ---
sql_file = "releases.sql"
years = []

with open(sql_file, "r", encoding="utf-8") as f:
    for line in f:
        matches = re.findall(r'\((.*?)\)', line)
        for match in matches:
            cols = [c.strip() for c in match.split(',')]
            if len(cols) >= 5:
                year = cols[2]
                if year != "NULL":
                    years.append(int(year))

# --- Step 2: Count games per year ---
counts = Counter(years)
sorted_years = sorted(counts)
num_games_values = [counts[y] for y in sorted_years]

# --- Step 3: Determine threshold for broken axis ---
# Adjust this depending on what you consider "outliers"
threshold = 1000  

# --- Step 4: Create broken-axis plot ---
fig = plt.figure(figsize=(12, 6), facecolor='none')  # transparent figure
gs = gridspec.GridSpec(2, 1, height_ratios=[1, 3], hspace=0.1)  # top is smaller

# Top plot for outliers
ax_top = plt.subplot(gs[0], facecolor='none')
ax_top.bar(sorted_years, num_games_values, color='skyblue')
ax_top.set_ylim(threshold, max(num_games_values)*1.1)
ax_top.spines['bottom'].set_visible(False)
ax_top.tick_params(bottom=False)
ax_top.grid(axis='y', linestyle='--', alpha=0.5)
ax_top.set_xticklabels(['']*len(sorted_years))  # hide labels
ax_top.set_xlim(1975, 2030)

# Bottom plot for normal range
ax_bottom = plt.subplot(gs[1], facecolor='none')
ax_bottom.bar(sorted_years, num_games_values, color='skyblue')
ax_bottom.set_xlim(1975, 2030)
ax_bottom.set_ylim(0, threshold)
ax_bottom.spines['top'].set_visible(False)
ax_bottom.grid(axis='y', linestyle='--', alpha=0.5)

# Diagonal break marks
d = 0.005  # size of diagonal lines
kwargs = dict(transform=ax_top.transAxes, color='w', clip_on=False)
ax_top.plot((-d, +d), (-8*d, +8*d), **kwargs)
ax_top.plot((1-d, 1+d), (-8*d, +8*d), **kwargs)
kwargs.update(transform=ax_bottom.transAxes)
ax_bottom.plot((-d, +d), (1-3*d, 1+3*d), **kwargs)
ax_bottom.plot((1-d, 1+d), (1-3*d, 1+3*d), **kwargs)

# X-axis labels and title
plt.xticks(range(1975, sorted_years[-1]+1, 5))  # vertical lines every 5 years
ax_top.set_xticks(range(1975, sorted_years[-1]+1, 5))  # vertical lines every 5 years
ax_top.set_yticks(range(1000, 4500, 1000))  # horz

# Set dark theme: white text and grid lines
for ax in [ax_top, ax_bottom]:
    ax.tick_params(colors='white', which='both')       # tick labels
    ax.spines['bottom'].set_color('white')
    ax.spines['top'].set_color('white')
    ax.spines['left'].set_color('white')
    ax.spines['right'].set_color('white')
    ax.yaxis.label.set_color('white')
    ax.xaxis.label.set_color('white')
    ax.title.set_color('white')
    
# Grid lines
ax_top.grid(axis='y', linestyle='--', alpha=0.5, color='white')
ax_bottom.grid(axis='y', linestyle='--', alpha=0.5, color='white')
ax_bottom.grid(axis='x', linestyle=':', alpha=0.5, color='white')
#plt.xlabel("Year")
#plt.ylabel("Number of Games")
#plt.suptitle("Software releases by year (source: ZXDB)",
#    color="white",     # title color
#    fontsize=18,       # slightly larger font
#    y=0.94             # move it closer to the plots (default ~0.98)
#)
plt.grid(axis='x', linestyle='--', alpha=0.5)              # vertical grid lines
ax_top.grid(axis='x', linestyle='--', alpha=0.5)              # vertical grid lines

#gs = gridspec.GridSpec(2, 1, height_ratios=[1, 3], hspace=0.05)

plt.tight_layout()
plt.savefig("/home/albi/Albi/Albi/Siti/annali/assets/2026-01-16--ttt-in-detail/entries-by-year.png", transparent=True, dpi=300)
#plt.show()

