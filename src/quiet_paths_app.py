
from flask import Flask
from flask_cors import CORS
from flask import jsonify
import json
import geopandas as gpd
import utils.files as files
import utils.routing as rt
import utils.geometry as geom_utils
import utils.networks as nw
import utils.exposures as exps
import utils.quiet_paths as qp
import utils.utils as utils
from fiona.crs import from_epsg
import time

app = Flask(__name__)
CORS(app)

# READ DATA
noise_polys = files.get_noise_polygons()
graph = files.get_network_kumpula_noise()
print('Data read.')
# SET NOISE COSTS
nts = [0.1, 0.15, 0.25, 0.5, 1, 1.5, 2, 4, 6]
nw.set_graph_noise_costs(graph, nts)
print('Noise costs set.')
# EXTRACT GRAPH FEATURES
edge_dicts = nw.get_all_edge_dicts(graph)
edge_gdf = nw.get_edge_gdf(edge_dicts, ['uvkey', 'geometry'])
node_gdf = nw.get_node_gdf(graph)
print('Network features extracted.')
edges_sind = edge_gdf.sindex
nodes_sind = node_gdf.sindex
print('Network ready.')

@app.route('/')
def hello_world():
    return 'Hello, World!'

@app.route('/shortestpath/<from_lat>,<from_lon>/<to_lat>,<to_lon>')
def get_shortest_path(from_lat, from_lon, to_lat, to_lon):
    from_latLon = {'lat': float(from_lat), 'lon': float(from_lon)}
    to_latLon = {'lat': float(to_lat), 'lon': float(to_lon)}
    print('from:', from_latLon)
    print('to:', to_latLon)
    from_xy = geom_utils.get_xy_from_lat_lon(from_latLon)
    to_xy = geom_utils.get_xy_from_lat_lon(to_latLon)
    print('from:', from_xy)
    print('to:', to_xy)
    orig_node = rt.get_nearest_node(graph, from_xy, edge_gdf, node_gdf, [], False, noise_polys)
    target_node = rt.get_nearest_node(graph, to_xy, edge_gdf, node_gdf, [], False, noise_polys)
    shortest_path = rt.get_shortest_path(graph, orig_node, target_node, 'length')
    path_geom = nw.get_edge_geoms_attrs(graph, shortest_path, 'length', True, False)
    feature = geom_utils.get_geojson_from_geom(path_geom['geometry'])
    feature['properties']['length'] = path_geom['total_length']
    feature['properties']['origin_node'] = orig_node
    feature['properties']['target_node'] = target_node
    print('feature', jsonify(feature))
    return jsonify(feature)

@app.route('/quietpaths/<from_lat>,<from_lon>/<to_lat>,<to_lon>')
def get_quiet_path(from_lat, from_lon, to_lat, to_lon):
    # get origin & target nodes
    from_latLon = {'lat': float(from_lat), 'lon': float(from_lon)}
    to_latLon = {'lat': float(to_lat), 'lon': float(to_lon)}
    # print('from:', from_latLon)
    # print('to:', to_latLon)
    from_xy = geom_utils.get_xy_from_lat_lon(from_latLon)
    to_xy = geom_utils.get_xy_from_lat_lon(to_latLon)
    print('from:', from_xy)
    print('to:', to_xy)
    orig_node = rt.get_nearest_node(graph, from_xy, edge_gdf, node_gdf, [], False, noise_polys)
    target_node = rt.get_nearest_node(graph, to_xy, edge_gdf, node_gdf, [], False, noise_polys)
    # get shortest path
    path_list = []
    shortest_path = rt.get_shortest_path(graph, orig_node, target_node, 'length')
    path_geom = nw.get_edge_geoms_attrs(graph, shortest_path, 'length', True, True)
    path_list.append({**path_geom, **{'id': 'short_p','type': 'short', 'nt': 0}})
    # get quiet paths to list
    for nt in nts:
        cost_attr = 'nc_'+str(nt)
        shortest_path = rt.get_shortest_path(graph, orig_node, target_node, cost_attr)
        path_geom = nw.get_edge_geoms_attrs(graph, shortest_path, cost_attr, True, True)
        path_list.append({**path_geom, **{'id': 'q_'+str(nt), 'type': 'quiet', 'nt': nt}})
    # collect quiet paths to gdf
    gdf = gpd.GeoDataFrame(path_list, crs=from_epsg(3879))
    paths_gdf = rt.aggregate_quiet_paths(gdf)
    # get exposures to noises along the paths
    # paths_gdf['noises'] = [exps.get_exposures_for_geom(line_geom, noise_polys) for line_geom in paths_gdf['geometry']]
    paths_gdf['th_noises'] = [exps.get_th_exposures(noises, [55, 60, 65, 70]) for noises in paths_gdf['noises']]
    # add noise exposure index (same as noise cost with noise tolerance: 1)
    costs = { 50: 0.1, 55: 0.2, 60: 0.3, 65: 0.4, 70: 0.5, 75: 0.6 }
    paths_gdf['nei'] = [round(nw.get_noise_cost(noises, costs, 1), 1) for noises in paths_gdf['noises']]
    paths_gdf['nei_norm'] = paths_gdf.apply(lambda row: round(row.nei / (0.6 * row.total_length), 2), axis=1)
    # add attributes of changes between shortest and quiet path noises
    path_comps = rt.get_short_quiet_paths_comparison(paths_gdf)
    return jsonify(qp.get_geojson_from_q_path_gdf(path_comps))

if __name__ == '__main__':
    app.run(host='0.0.0.0')
