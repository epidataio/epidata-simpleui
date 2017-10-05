EpiData Simple Dashboard
=====================================

Installation
-------------
The simple dashboard example leverages Python's Pandas, Flask and Bokeh packages. Install these packages using the command below:  
    pip install pandas==0.19.2 bokeh==0.12.9 flask==0.12.2

Install simple dashboard by cloning the epidataio/epidata-simpleui repository:  
    git clone https://github.com/epidataio/epidata-simpleui.git

Configuration and Launch
-------------------------
Replace 'API Token' in simple_dashboard.py with the application token specified during EpiData launch.

Change current directory to 'epidata-simpleui' diectory.

Launch simple dashboard using python command. For instance:  
    python simple_dashboard.py --host <epidata-url>

Resources
----------
Additional information on Flask and Bokeh is available at:  
    http://flask.pocoo.org/  
    https://bokeh.pydata.org/en/latest/

