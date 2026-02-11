for file in _site/20*/*/*/*html _site/projects/*html ; do 
    echo $file ; 
    echo
    echo '<div class="toc" markdown="1">' ; 
    echo '  <a href="/index.html"><img src="/assets/index/homepage.png" width="32" style="border: 0px"/></a>' ; 
    echo '  <h2>Contents</h2>' ;
    echo '  <ul>' ;
    echo '    <li><a href="#top-of-page">(Top)</a></li>' 
    grep --only-matching -P '<h2 id=[^>]*>.*(?=</h2)' $file | \
        while read -r line ; do 
            printf '    <li><a href="#%s">%s</a></li>\n' \
                "$( printf "$line" | grep --only-matching -P 'id="\K[^"]*' )" \
                "$( printf "$line" | grep --only-matching -P '">\K.*' )" \
                ;
        done
    echo '  </ul>' ;
    echo '</div>' ;
    echo '' ;
    echo '<div class="content" markdown="1">' ;
    echo '<a id="top-of-page"/>' ;
    echo
done
