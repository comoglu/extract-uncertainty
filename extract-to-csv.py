#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SeisComp Uncertainty Extractor

This script extracts event information from SeisComp XML files with a focus on
location uncertainty parameters. It outputs a CSV file containing event coordinates,
origin time, and various uncertainty metrics.

Usage: python seiscomp_uncertainty_extractor.py <input_xml_file> <output_csv_file>
"""

import sys
import os
import argparse
import csv
import xml.etree.ElementTree as ET
from datetime import datetime


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Extract seismic event uncertainty information from SeisComp XML files.')
    parser.add_argument('input_file', help='Input SeisComp XML file')
    parser.add_argument('output_file', help='Output CSV file')
    parser.add_argument('--delimiter', default=',',
                        help='CSV delimiter (default: comma)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose output')

    return parser.parse_args()


def detect_namespace(root):
    """Detect the SeisComp namespace from XML root element."""
    namespaces = {
        '0.13': 'http://geofon.gfz-potsdam.de/ns/seiscomp3-schema/0.13',
        '0.12': 'http://geofon.gfz-potsdam.de/ns/seiscomp3-schema/0.12',
        '0.11': 'http://geofon.gfz-potsdam.de/ns/seiscomp3-schema/0.11',
        '0.10': 'http://geofon.gfz-potsdam.de/ns/seiscomp3-schema/0.10',
        'seiscomp': 'http://geofon.gfz-potsdam.de/ns/seiscomp/0.1'
    }

    # First check if we have a namespace in the root tag
    if '}' in root.tag:
        ns_uri = root.tag.split('}')[0][1:]
        return {'ns': ns_uri}

    # Then check for xmlns attributes
    for key, uri in namespaces.items():
        for attr_name, attr_value in root.attrib.items():
            if attr_value == uri or (attr_name == f'xmlns:{key}' and attr_value):
                return {'ns': uri}

    # Finally check the schema version attribute
    version = root.get('version')
    if version and version in namespaces:
        return {'ns': namespaces[version]}

    return None


def get_element_text(element, xpath, ns=None, default=''):
    """Helper method to safely get element text with namespace support."""
    try:
        elem = element.find(xpath, ns) if ns else element.find(xpath)
        return elem.text if elem is not None and elem.text else default
    except Exception:
        return default


def get_time_value(element, ns=None):
    """Extract time value from element with namespace support."""
    try:
        # Try different possible paths for time value
        time_elem = None

        if ns:
            paths = [
                ".//ns:time/ns:value",
                ".//ns:timeValue",
                ".//ns:Time/ns:value"
            ]
            for path in paths:
                time_elem = element.find(path, ns)
                if time_elem is not None:
                    break
        else:
            paths = [
                ".//time/value",
                ".//timeValue",
                ".//Time/value"
            ]
            for path in paths:
                time_elem = element.find(path)
                if time_elem is not None:
                    break

        if time_elem is not None and time_elem.text:
            try:
                # Handle ISO format with timezone
                return datetime.fromisoformat(time_elem.text.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                return time_elem.text
    except Exception as e:
        if args.verbose:
            print(f"Error extracting time value: {str(e)}")
    return ''


def get_value(element, tag, ns=None):
    """Get value from element with namespace support."""
    try:
        if ns:
            value_elem = element.find(f".//ns:{tag}/ns:value", ns)
        else:
            value_elem = element.find(f".//{tag}/value")

        return value_elem.text if value_elem is not None else ''
    except Exception:
        return ''


def get_value_with_uncertainty(element, tag, ns=None):
    """Extract a value and its uncertainty."""
    value = ''
    uncertainty = ''
    confidence_level = ''

    try:
        # Get the main value
        if ns:
            value_elem = element.find(f".//ns:{tag}/ns:value", ns)
        else:
            value_elem = element.find(f".//{tag}/value")

        if value_elem is not None:
            value = value_elem.text

        # Get uncertainty
        if ns:
            uncertainty_elem = element.find(f".//ns:{tag}/ns:uncertainty", ns)
        else:
            uncertainty_elem = element.find(f".//{tag}/uncertainty")

        if uncertainty_elem is not None:
            uncertainty = uncertainty_elem.text

        # Get confidence level
        if ns:
            confidence_elem = element.find(
                f".//ns:{tag}/ns:confidenceLevel", ns)
        else:
            confidence_elem = element.find(f".//{tag}/confidenceLevel")

        if confidence_elem is not None:
            confidence_level = confidence_elem.text

        # Get lower and upper uncertainty bounds if available
        lower_uncertainty = get_element_text(
            element, f".//ns:{tag}/ns:lowerUncertainty" if ns else f".//{tag}/lowerUncertainty", ns)
        upper_uncertainty = get_element_text(
            element, f".//ns:{tag}/ns:upperUncertainty" if ns else f".//{tag}/upperUncertainty", ns)

        return {
            'value': value,
            'uncertainty': uncertainty,
            'confidenceLevel': confidence_level,
            'lowerUncertainty': lower_uncertainty,
            'upperUncertainty': upper_uncertainty
        }
    except Exception as e:
        if args.verbose:
            print(f"Error getting value with uncertainty for {tag}: {str(e)}")
        return {
            'value': value,
            'uncertainty': uncertainty,
            'confidenceLevel': confidence_level,
            'lowerUncertainty': '',
            'upperUncertainty': ''
        }


def extract_confidence_ellipsoid(origin, ns=None):
    """Extract confidence ellipsoid information."""
    ellipsoid = {}

    try:
        confidence_ellipsoid = origin.find(
            ".//ns:confidenceEllipsoid" if ns else ".//confidenceEllipsoid", ns)

        if confidence_ellipsoid is not None:
            ellipsoid['semiMajorAxisLength'] = get_element_text(confidence_ellipsoid,
                                                                ".//ns:semiMajorAxisLength" if ns else ".//semiMajorAxisLength", ns)
            ellipsoid['semiMinorAxisLength'] = get_element_text(confidence_ellipsoid,
                                                                ".//ns:semiMinorAxisLength" if ns else ".//semiMinorAxisLength", ns)
            ellipsoid['semiIntermediateAxisLength'] = get_element_text(confidence_ellipsoid,
                                                                       ".//ns:semiIntermediateAxisLength" if ns else ".//semiIntermediateAxisLength", ns)
            ellipsoid['majorAxisPlunge'] = get_element_text(confidence_ellipsoid,
                                                            ".//ns:majorAxisPlunge" if ns else ".//majorAxisPlunge", ns)
            ellipsoid['majorAxisAzimuth'] = get_element_text(confidence_ellipsoid,
                                                             ".//ns:majorAxisAzimuth" if ns else ".//majorAxisAzimuth", ns)
            ellipsoid['majorAxisRotation'] = get_element_text(confidence_ellipsoid,
                                                              ".//ns:majorAxisRotation" if ns else ".//majorAxisRotation", ns)
    except Exception as e:
        if args.verbose:
            print(f"Error extracting confidence ellipsoid: {str(e)}")

    return ellipsoid


def extract_origin_quality(origin, ns=None):
    """Extract origin quality parameters."""
    quality = {}

    try:
        quality_elem = origin.find(".//ns:quality" if ns else ".//quality", ns)

        if quality_elem is not None:
            quality['associatedPhaseCount'] = get_element_text(quality_elem,
                                                               ".//ns:associatedPhaseCount" if ns else ".//associatedPhaseCount", ns)
            quality['usedPhaseCount'] = get_element_text(quality_elem,
                                                         ".//ns:usedPhaseCount" if ns else ".//usedPhaseCount", ns)
            quality['associatedStationCount'] = get_element_text(quality_elem,
                                                                 ".//ns:associatedStationCount" if ns else ".//associatedStationCount", ns)
            quality['usedStationCount'] = get_element_text(quality_elem,
                                                           ".//ns:usedStationCount" if ns else ".//usedStationCount", ns)
            quality['standardError'] = get_element_text(quality_elem,
                                                        ".//ns:standardError" if ns else ".//standardError", ns)
            quality['azimuthalGap'] = get_element_text(quality_elem,
                                                       ".//ns:azimuthalGap" if ns else ".//azimuthalGap", ns)
            quality['minimumDistance'] = get_element_text(quality_elem,
                                                          ".//ns:minimumDistance" if ns else ".//minimumDistance", ns)
            quality['maximumDistance'] = get_element_text(quality_elem,
                                                          ".//ns:maximumDistance" if ns else ".//maximumDistance", ns)
    except Exception as e:
        if args.verbose:
            print(f"Error extracting origin quality: {str(e)}")

    return quality


def extract_origin_uncertainty(origin, ns=None):
    """Extract comprehensive uncertainty information from an origin."""
    data = {}

    # Basic origin data
    data['originID'] = origin.get('publicID', '')
    data['time'] = get_time_value(origin, ns)

    # Extract latitude with uncertainty
    lat_data = get_value_with_uncertainty(origin, 'latitude', ns)
    data['latitude'] = lat_data['value']
    data['latitudeUncertainty'] = lat_data['uncertainty']
    data['latitudeLowerUncertainty'] = lat_data['lowerUncertainty']
    data['latitudeUpperUncertainty'] = lat_data['upperUncertainty']

    # Extract longitude with uncertainty
    lon_data = get_value_with_uncertainty(origin, 'longitude', ns)
    data['longitude'] = lon_data['value']
    data['longitudeUncertainty'] = lon_data['uncertainty']
    data['longitudeLowerUncertainty'] = lon_data['lowerUncertainty']
    data['longitudeUpperUncertainty'] = lon_data['upperUncertainty']

    # Extract depth with uncertainty
    depth_data = get_value_with_uncertainty(origin, 'depth', ns)
    data['depth'] = depth_data['value']
    data['depthUncertainty'] = depth_data['uncertainty']
    data['depthLowerUncertainty'] = depth_data['lowerUncertainty']
    data['depthUpperUncertainty'] = depth_data['upperUncertainty']

    # Extract origin uncertainty
    origin_uncertainty = origin.find(
        ".//ns:originUncertainty" if ns else ".//originUncertainty", ns)
    if origin_uncertainty is not None:
        data['horizontalUncertainty'] = get_element_text(origin_uncertainty,
                                                         ".//ns:horizontalUncertainty" if ns else ".//horizontalUncertainty", ns)
        data['minHorizontalUncertainty'] = get_element_text(origin_uncertainty,
                                                            ".//ns:minHorizontalUncertainty" if ns else ".//minHorizontalUncertainty", ns)
        data['maxHorizontalUncertainty'] = get_element_text(origin_uncertainty,
                                                            ".//ns:maxHorizontalUncertainty" if ns else ".//maxHorizontalUncertainty", ns)
        data['azimuthMaxHorizontalUncertainty'] = get_element_text(origin_uncertainty,
                                                                   ".//ns:azimuthMaxHorizontalUncertainty" if ns else ".//azimuthMaxHorizontalUncertainty", ns)
        data['confidenceLevel'] = get_element_text(origin_uncertainty,
                                                   ".//ns:confidenceLevel" if ns else ".//confidenceLevel", ns)
        data['preferredDescription'] = get_element_text(origin_uncertainty,
                                                        ".//ns:preferredDescription" if ns else ".//preferredDescription", ns)

    # Extract confidence ellipsoid
    ellipsoid = extract_confidence_ellipsoid(origin, ns)
    for key, value in ellipsoid.items():
        data[key] = value

    # Extract quality parameters
    quality = extract_origin_quality(origin, ns)
    for key, value in quality.items():
        data[key] = value

    # Evaluation information
    data['evaluationMode'] = get_element_text(
        origin, ".//ns:evaluationMode" if ns else ".//evaluationMode", ns)
    data['evaluationStatus'] = get_element_text(
        origin, ".//ns:evaluationStatus" if ns else ".//evaluationStatus", ns)

    return data


def extract_events(root, ns=None):
    """Extract events and their origins from the XML."""
    events_data = []

    try:
        # Find EventParameters element
        event_parameters = root.find(
            ".//ns:EventParameters" if ns else ".//EventParameters", ns)

        if event_parameters is None:
            print("No EventParameters found in XML")
            return events_data

        # Find all events
        event_elements = event_parameters.findall(
            ".//ns:event" if ns else ".//event", ns)

        if args.verbose:
            print(f"Found {len(event_elements)} events")

        # Process each event
        for event in event_elements:
            event_id = event.get('publicID', '')

            if args.verbose:
                print(f"Processing event: {event_id}")

            # Find preferred origin ID
            preferred_origin_id = get_element_text(
                event, ".//ns:preferredOriginID" if ns else ".//preferredOriginID", ns)

            # Find region name for the event
            region_name = ''
            event_descriptions = event.findall(
                ".//ns:description" if ns else ".//description", ns)
            for desc in event_descriptions:
                type_elem = desc.find(".//ns:type" if ns else ".//type", ns)
                if type_elem is not None and type_elem.text == "region name":
                    text_elem = desc.find(
                        ".//ns:text" if ns else ".//text", ns)
                    if text_elem is not None:
                        region_name = text_elem.text
                        break

            # Find origins
            if preferred_origin_id:
                # First try to find the preferred origin
                for origin in event_parameters.findall(".//ns:origin" if ns else ".//origin", ns):
                    origin_id = origin.get('publicID', '')

                    if origin_id == preferred_origin_id:
                        # Extract origin data with uncertainty information
                        origin_data = extract_origin_uncertainty(origin, ns)

                        # Add event information
                        origin_data['eventID'] = event_id
                        origin_data['regionName'] = region_name
                        origin_data['isPreferredOrigin'] = 'true'

                        events_data.append(origin_data)

                        if args.verbose:
                            print(f"  Added preferred origin: {origin_id}")
            else:
                # If no preferred origin, take all origins for this event
                event_org_count = 0

                # Get all origins directly from EventParameters
                for origin in event_parameters.findall(".//ns:origin" if ns else ".//origin", ns):
                    origin_id = origin.get('publicID', '')

                    # Extract origin data
                    origin_data = extract_origin_uncertainty(origin, ns)

                    # Add event information
                    origin_data['eventID'] = event_id
                    origin_data['regionName'] = region_name
                    origin_data['isPreferredOrigin'] = 'false'

                    events_data.append(origin_data)
                    event_org_count += 1

                if args.verbose:
                    print(
                        f"  Added {event_org_count} origins (no preferred origin specified)")

    except Exception as e:
        print(f"Error extracting events: {str(e)}")

    return events_data


def main():
    """Main function to run the script."""
    global args
    args = parse_arguments()

    # Check if input file exists
    if not os.path.isfile(args.input_file):
        print(f"Error: Input file '{args.input_file}' does not exist")
        return 1

    print(f"Processing file: {args.input_file}")

    try:
        # Parse XML file
        tree = ET.parse(args.input_file)
        root = tree.getroot()

        # Detect namespace
        ns = detect_namespace(root)
        if args.verbose and ns:
            print(f"Detected namespace: {ns['ns']}")

        # Extract events and their origins with uncertainty information
        events_data = extract_events(root, ns)

        if not events_data:
            print("No events with uncertainty information found in the file")
            return 1

        # Define CSV headers based on the first event
        headers = list(events_data[0].keys())

        # Write data to CSV
        with open(args.output_file, 'w', newline='') as csvfile:
            writer = csv.DictWriter(
                csvfile, fieldnames=headers, delimiter=args.delimiter)
            writer.writeheader()
            for data in events_data:
                writer.writerow(data)

        print(
            f"Successfully extracted uncertainty information for {len(events_data)} origins to {args.output_file}")
        return 0

    except Exception as e:
        print(f"Error processing XML file: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
