import utils.geometry as geom_utils

def get_similar_length_paths(paths, path):
    path_len = path['properties']['length']
    similar_len_paths = [path for path in paths if (path['properties']['length'] < (path_len + 25)) & (path['properties']['length'] > (path_len - 25))]
    return similar_len_paths

def get_overlapping_paths(compare_paths, path, tolerance=None):
    overlapping = [path]
    path_geom = path['properties']['geometry']
    path_geom_buff = path_geom.buffer(tolerance)
    for compare_path in [compare_path for compare_path in compare_paths if path['properties']['id'] != compare_path['properties']['id']]:
        comp_path_geom = compare_path['properties']['geometry']
        if (comp_path_geom.within(path_geom_buff)):
            # print('found overlap:', path['properties']['id'], compare_path['properties']['id'])
            overlapping.append(compare_path)
    return overlapping

def get_best_path(paths):
    ordered = paths.copy()
    def get_score(path):
        return path['properties']['nei_norm']
    ordered.sort(key=get_score)
    # print('ordered (best=[0]):', [(path['properties']['id'], path['properties']['nei_norm']) for path in ordered])
    return ordered[0]

def remove_duplicate_geom_paths(paths, tolerance=None):
    filtered_paths_ids = []
    filtered_paths = []
    quiet_paths = [path for path in paths if path['properties']['type'] == 'quiet']
    shortest_path = [path for path in paths if path['properties']['type'] == 'short'][0]
    # function for returning better of two paths
    for path in quiet_paths:
        if (path['properties']['type'] != 'short'):
            path_id = path['properties']['id']
            similar_len_paths = get_similar_length_paths(paths, path)
            overlapping_paths = get_overlapping_paths(similar_len_paths, path, tolerance)
            best_overlapping_path = get_best_path(overlapping_paths)
            if (len(best_overlapping_path) > 0):
                best_overlapping_id = best_overlapping_path['properties']['id']
                if (best_overlapping_id not in filtered_paths_ids):
                    filtered_paths.append(best_overlapping_path)
                    filtered_paths_ids.append(best_overlapping_id)
            else:
                if (path_id not in filtered_paths_ids):
                    filtered_paths.append(path)
                    filtered_paths_ids.append(path_id)
    # check if shortest path is shorter than shortest quiet path
    shortest_quiet_path = filtered_paths[0]
    if (shortest_quiet_path['properties']['length'] - shortest_path['properties']['length'] > 10):
        # print('set shortest path as shortest')
        filtered_paths.append(shortest_path)
    else:
        # print('set shortest quiet path as shortest')
        filtered_paths[0]['properties']['type'] = 'short'
        filtered_paths[0]['properties']['id'] = 'short_p'
    print('found', len(paths), 'of which returned', len(filtered_paths), 'unique paths.')
    # delete shapely geometries from path dicts
    for path in filtered_paths:
        del path['properties']['geometry']
    return filtered_paths

def get_geojson_from_q_path_gdf(gdf):
    features = []
    for path in gdf.itertuples():
        feature_d = geom_utils.get_geojson_from_geom(getattr(path, 'geometry'))
        feature_d['properties']['type'] = getattr(path, 'type')
        feature_d['properties']['id'] = getattr(path, 'id')
        feature_d['properties']['length'] = getattr(path, 'total_length')
        feature_d['properties']['min_nt'] = getattr(path, 'min_nt')
        feature_d['properties']['max_nt'] = getattr(path, 'max_nt')
        # feature_d['properties']['len_diff'] = getattr(path, 'len_diff')
        # feature_d['properties']['len_diff_rat'] = getattr(path, 'len_diff_rat')
        feature_d['properties']['noises'] = getattr(path, 'noises')
        # feature_d['properties']['noises_diff'] = getattr(path, 'noises_diff')
        feature_d['properties']['th_noises'] = getattr(path, 'th_noises')
        # feature_d['properties']['th_noises_diff'] = getattr(path, 'th_noises_diff')
        feature_d['properties']['nei'] = getattr(path, 'nei')
        feature_d['properties']['nei_norm'] = getattr(path, 'nei_norm')
        # feature_d['properties']['nei_diff_rat'] = getattr(path, 'nei_diff_rat')
        # feature_d['properties']['path_score'] = getattr(path, 'path_score')
        feature_d['properties']['geometry'] = getattr(path, 'geometry')
        features.append(feature_d)
    
    return features
