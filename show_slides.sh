#!/usr/bin/env sh
pip install -r slides_requirements.txt
ipython nbconvert medbot.ipynb --to slides --post serve --reveal-prefix http://cdn.jsdelivr.net/reveal.js/2.6.2
