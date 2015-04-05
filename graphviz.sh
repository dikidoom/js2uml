#!/bin/bash

#dot -Tsvg -odot.svg dot.dot 
dot -Tpng -odot.png dot.dot 
open dot.png
