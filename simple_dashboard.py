###########################
# Import Required Modules #
###########################

from flask import Flask, jsonify, make_response, render_template, request, current_app
import argparse
from datetime import datetime, timedelta
import httplib, json, time, urllib, urllib2
from pytz import UTC, timezone
import pandas as pd
import numpy as np
from pandas.io.json import json_normalize
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource
from bokeh.models.sources import AjaxDataSource
from bokeh.embed import components
from bokeh.resources import INLINE
from functools import update_wrapper, wraps
from six import string_types

app = Flask(__name__)


##################################
# Define Variables and Functions #
##################################

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument('--host')
args = arg_parser.parse_args()

HOST = args.host or '127.0.0.1'
AUTHENTICATION_URL = 'https://' + HOST + '/authenticate/app'
AUTHENTICATION_ROUTE = '/authenticate/app'
QUERY_MEASUREMENTS_ORIGINAL_URL = 'https://' + HOST + '/measurements_original?'
QUERY_MEASUREMENTS_CLEANSED_URL = 'https://' + HOST + '/measurements_cleansed?'
QUERY_MEASUREMENTS_SUMMARY_URL = 'https://' + HOST + '/measurements_summary?'

def get_time(time_string):
    date_object = datetime.strptime(time_string, '%m/%d/%Y %H:%M:%S.%f')
    return long(time.mktime(date_object.timetuple()) * 1e3 + date_object.microsecond / 1e3)

def add_time(time_string, delta):
    date_object = datetime.strptime(time_string, '%m/%d/%Y %H:%M:%S.%f') + timedelta(seconds=delta)
    return long(time.mktime(date_object.timetuple()) * 1e3 + date_object.microsecond / 1e3)

current_time_string = datetime.now().strftime("%m/%d/%Y %H:%M:%S.%f")
current_time = get_time(current_time_string)


#####################
# EDIT THIS SECTION #
#####################

# Replace quoted string with API Token or GitHub Personal Access Token (REQUIRED)
ACCESS_TOKEN = 'API Token'

# Specify Query Parameters
COMPANY ='EpiData'
SITE = 'Redwood_City'
STATION = 'WSN-1'
SENSOR = "Temperature_Probe"
meas_name = "Temperature"
begin_time = get_time("9/20/2017 00:00:00.000")
end_time = get_time("10/4/2017 00:00:00.000")
parameters = {'company': COMPANY, 'site': SITE, 'station': STATION, 'sensor': SENSOR, 'beginTime': begin_time, 'endTime': end_time}


#########################
# SKIP SSL VERIFICATION #
#########################

import ssl

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    # Legacy Python that doesn't verify HTTPS certificates by default
    pass
else:
    # Handle target environment that doesn't support HTTPS verification
    ssl._create_default_https_context = _create_unverified_https_context


#############################
# Authenticate with EpiData #
#############################

conn = httplib.HTTPSConnection(HOST)

# Authentication is achieved by posting to the AUTHENTICATION_URL.
url = AUTHENTICATION_URL

# An HTTP POST with JSON content requires the HTTP Content-type header.
json_header = {'Content-type': 'application/json'}

# The access token is povided via JSON.
json_body = json.dumps({'accessToken': ACCESS_TOKEN})

# Send the POST request and receive the HTTP response.
conn.request('POST', AUTHENTICATION_ROUTE, json_body, json_header)
post_response = conn.getresponse()
response_status = post_response.status
response_text = post_response.read()

# Check that the response's HTTP response code is 200 (OK).
assert response_status == 200

# Parse the JSON response.
response_json = json.loads(response_text)

# Retrieve the new session id from the JSON response.
session_id = response_json['sessionId']

# Construct the session cookie.
session_cookie = 'epidata=' + session_id


######################################
# Query and Plot Data using REST API #
######################################

@app.route('/simpleui/data', methods=['GET', 'OPTIONS', 'POST'])
def query_data():

    try:
 
        # Create instances that connect to the server
        conn = httplib.HTTPSConnection(HOST)

        # Construct url with parameters
        url = request.args.get('url')+urllib.urlencode(parameters)
        json_header = {'Cookie': session_cookie, 'Accept': 'text/plain'}

        # Send the GET request and receive the HTTP response.
        conn.request('GET', url, "", json_header)
        get_response = conn.getresponse()
        response_status = get_response.status
        response_text = get_response.read()
               
        # Check that the response's HTTP response code is 200 (OK) and read the response.
        assert response_status == 200
        measurements = json.loads(response_text)
       
        # Convert HTTP response to Pandas DataFrame
        if (measurements['records']):
            df = json_normalize(measurements['records'])
            df = df.loc[df["meas_name"]==meas_name]    
            df = df[["ts", "meas_value"]]
        else:
            df = pd.DataFrame(columns = ["ts", "meas_value"])

        output = jsonify(timestamp=df["ts"].tolist(), meas_value=df["meas_value"].tolist())
        return output

    except (KeyboardInterrupt, SystemExit):
        print '\n...Program Stopped Manually!'
        raise


# Create Bokeh Plots
def create_chart(title, source_data, meas_name, PLOT_OPTIONS, color):

    plot = figure(title=title, **PLOT_OPTIONS)
    plot.circle("timestamp", "meas_value", source=source_data, legend=meas_name, line_color=color, line_width=1.5)
    line = plot.line("timestamp", "meas_value", source=source_data, legend=meas_name, line_color=color, line_width=1.5)
    plot.legend.location = "top_right"

    return plot


def crossdomain(origin=None, methods=None, headers=None,
                max_age=21600, attach_to_all=True,
                automatic_options=True):
    """
    Decorator to set crossdomain configuration on a Flask view

    For more details about it refer to:

    http://flask.pocoo.org/snippets/56/
    """
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))

    if headers is not None and not isinstance(headers, string_types):
        headers = ', '.join(x.upper() for x in headers)

    if not isinstance(origin, string_types):
        origin = ', '.join(origin)

    if isinstance(max_age, timedelta):
        max_age = max_age.total_seconds()

    def get_methods():
        options_resp = current_app.make_default_options_response()
        return options_resp.headers['allow']

    def decorator(f):
        @wraps(f)
        def wrapped_function(*args, **kwargs):
            if automatic_options and request.method == 'OPTIONS':
                resp = current_app.make_default_options_response()
            else:
                resp = make_response(f(*args, **kwargs))
            if not attach_to_all and request.method != 'OPTIONS':
                return resp

            h = resp.headers

            h['Access-Control-Allow-Origin'] = origin
            h['Access-Control-Allow-Methods'] = get_methods()
            h['Access-Control-Max-Age'] = str(max_age)
            requested_headers = request.headers.get(
                'Access-Control-Request-Headers'
            )
            if headers is not None:
                h['Access-Control-Allow-Headers'] = headers
            elif requested_headers:
                h['Access-Control-Allow-Headers'] = requested_headers
            return resp
        f.provide_automatic_options = False
        return update_wrapper(wrapped_function, f)

    return decorator


# Index Page
@app.route('/simpleui', methods=['GET'])
@crossdomain(origin="*", methods=['GET'])
def index():

    # Perform Query via AJAX
    source_original = AjaxDataSource(data_url="/simpleui/data?url="+QUERY_MEASUREMENTS_ORIGINAL_URL, method="GET", polling_interval=1000)
    source_processed = AjaxDataSource(data_url="/simpleui/data?url="+QUERY_MEASUREMENTS_CLEANSED_URL, method="GET", polling_interval=1000)
    source_original.data = dict(timestamp=[], meas_value=[])
    source_processed.data = dict(timestamp=[], meas_value=[])

    # Create Plots with Queried Data
    PLOT_OPTIONS = dict(plot_width=750, plot_height=200, x_axis_type='datetime', x_range=(begin_time, end_time), y_range=(30, 300))
    plot_original = create_chart("Original Measurements", source_original, meas_name, PLOT_OPTIONS, 'orangered')
    plot_processed = create_chart("Processed Measurements", source_processed, meas_name, PLOT_OPTIONS, 'blue')

    # Render HTML Page
    js_resources = INLINE.render_js()
    css_resources = INLINE.render_css()
    script, div = components({'original': plot_original, 'processed': plot_processed})
    return render_template("simple_dashboard.html", plot_script=script, plot_div=div, js_resources=js_resources, css_resources=css_resources)


if __name__ == '__main__':
	app.run(port=8070, debug=True)
