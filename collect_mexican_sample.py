## in this script we collect all the samples of the eukaryotic assemblies and try to fit their coordinates within the mexican boundaries
##
## 
##
## 2 types of attributes where we can extract from the samples: geo_loc_name: {"name": "lat_lon", "value": "38.9140 N 121.6147 E"} and latitude and longitude: {"name": "latitude", "value": "38.9140"} and {"name": "longitude", "value": "121.6147"}

#extract the coordinates from the samples

#fit the coordinates within the mexican boundaries

#write the matching assembly accessions to a file
import json 
import re

def parse_lat_lon(coord_string):
    """
    Convert strings like:
        '29.87 N 95.56 E'
        '19.43 N 99.13 W'
    
    Returns:
        (latitude_decimal, longitude_decimal)
    """
    
    if not coord_string:
        return None, None
    
    parts = coord_string.strip().upper().split()
    
    if len(parts) != 4:
        raise ValueError("Input must be: '<lat> <N/S> <lon> <E/W>'")
    
    lat_value = float(parts[0])
    lat_dir = parts[1]
    lon_value = float(parts[2])
    lon_dir = parts[3]
    
    # Apply sign
    if lat_dir == "S":
        lat_value = -abs(lat_value)
    elif lat_dir == "N":
        lat_value = abs(lat_value)
    else:
        raise ValueError("Latitude direction must be N or S")
    
    if lon_dir == "W":
        lon_value = -abs(lon_value)
    elif lon_dir == "E":
        lon_value = abs(lon_value)
    else:
        raise ValueError("Longitude direction must be E or W")
    
    return lat_value, lon_value


# Example
assemblies_within_mexican_boundaries = []


collected_locations = [] #tuples of (ass acc, biosample acc, latitude, longitude or geo_lat_lon)
with open('biosample_schemas.jsonl', 'r') as file:
    for line in file:
        data = json.loads(line)
        biosample = data.get('schema', {})
        biosample_accession = biosample.get('accession')
        biosample_attributes = biosample.get('attributes', {})
        geo_lat_lon = None
        latitude = None
        longitude = None
        for attribute in biosample_attributes:
            if attribute.get('name') == 'lat_lon':
                geo_lat_lon = attribute.get('value')
            elif attribute.get('name') == 'geographic location (latitude)':
                latitude = attribute.get('value')
            elif attribute.get('name') == 'geographic location (longitude)':
                longitude = attribute.get('value')
        #iterate over attributes and extract the latitude and longitude or geo_lat_lon
        if geo_lat_lon:
            collected_locations.append((data['accession'], biosample_accession, geo_lat_lon))
        elif latitude and longitude:
            collected_locations.append((data['accession'], biosample_accession, f"{latitude} {longitude}"))

#write the collected locations to a file
with open('collected_locations.jsonl', 'w') as file:
    for assembly_accession, biosample_accession, location in collected_locations:
        file.write(json.dumps(dict(assembly_accession=assembly_accession, biosample_accession=biosample_accession, location=location)) + '\n')

#now we parse the coordinates of each into latitude and longitude
mapped_locations = []
for assembly_accession, biosample_accession, location in collected_locations:
    try:
        parts = location.split(' ')
        if len(parts) == 4:
            latitude, longitude = parse_lat_lon(location)
        elif len(parts) == 2:
            latitude = float(parts[0])
            longitude = float(parts[1])
        else:
            raise ValueError(f"Invalid location format: {location}")
    except ValueError:
        continue
    mapped_locations.append((assembly_accession, biosample_accession, latitude, longitude))

with open('mapped_locations.jsonl', 'w') as file:
    for assembly_accession, biosample_accession, latitude, longitude in mapped_locations:
        file.write(json.dumps(dict(assembly_accession=assembly_accession, biosample_accession=biosample_accession, latitude=latitude, longitude=longitude)) + '\n')