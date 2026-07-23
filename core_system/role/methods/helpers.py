import re
from shared.services.settings_service import SettingsService


def chunkIt(seq, num):
    """
    Takes a list of n length and breaks it apart into the 'most' equal length list of num.  
    :param seq: 
    :param num: 
    :return: 
    """
    avg = len(seq) / float(num)
    out = []
    last = 0.0

    while last < len(seq):
        out.append(seq[int(last):int(last + avg)])
        last += avg

    return out


def permission_spacer(permission_name):
    ops_config = SettingsService.get_setting('OperationalEntities')
    special_perm = {'Villages': ops_config[0]['name'], 'Clusters': ops_config[1]['name'], 'Hubs': ops_config[2]['name'], 'Zones': ops_config[3]['name'], 'Regions': ops_config[4]['name']}
    if special_perm.get(permission_name):
        permission_name = special_perm.get(permission_name)
    return ' '.join(w for w in re.split('([A-z][a-z]+)', permission_name) if w)
