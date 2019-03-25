# IMPORT MODULES FOR NETWORK CONSTRUCTION
import pandas as pd
import geopandas as gpd
import osmnx as ox
import networkx as nx
from multiprocessing import current_process, Pool
import time
import utils.geometry as geom_utils
import utils.files as files
import utils.networks as nw
import utils.exposures as exps
import utils.utils as utils

# READ DATA
noise_polys = files.get_noise_polygons()
graph_proj = files.get_undirected_network_graph()
node_count = len(graph_proj)
print('Nodes in the graph:', node_count)
# get all edges as list of dicts
edge_dicts = nw.get_all_edge_dicts(graph_proj)
edge_count = len(edge_dicts)
print('Edges in the graph:', edge_count)
edge_dicts[:2]

# EXTRACT NOISES TO SEGMENTS QUICKLY
def get_segment_noises_df(edge_dicts):
    edge_gdf_sub = nw.get_edge_gdf(edge_dicts, ['geometry', 'length', 'uvkey'])
    # add noise split lines as list
    edge_gdf_sub['split_lines'] = [geom_utils.get_split_lines_list(line_geom, noise_polys) for line_geom in edge_gdf_sub['geometry']]
    # explode new rows from split lines column
    split_lines = nw.explode_edges_to_noise_parts(edge_gdf_sub)
    # join noises to split lines
    split_line_noises = exps.get_noise_attrs_to_split_lines(split_lines, noise_polys)
    # aggregate noises back to segments
    segment_noises = nw.aggregate_segment_noises(split_line_noises)
    return segment_noises

# edge_set = edge_dicts[:1000]
edge_chunks = utils.get_list_chunks(edge_dicts, 300)
pool = Pool(processes=15)
start_time = time.time()

segment_noise_dfs = pool.map(get_segment_noises_df, edge_chunks)

time_elapsed = round(time.time() - start_time, 1)
edge_time = round(time_elapsed/len(edge_dicts), 3)
print('\n--- %s seconds ---' % (round(time_elapsed, 1)))
print('--- %s seconds per edge ---' % (edge_time))

#%% UPDATE NOISES TO GRAPH
for segment_noises in segment_noise_dfs:
    nw.update_segment_noises(segment_noises, graph_proj)

ox.save_graphml(graph_proj, filename='kumpula_u_g_n.graphml', folder='graphs', gephi=False)
