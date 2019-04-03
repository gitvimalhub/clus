from typing import Callable

from clus.src.core.methods import kmeans
from clus.src.core.methods import fuzzy_c_means
from clus.src.core.methods import hard_c_medoids
from clus.src.core.methods import fuzzy_c_medoids
from clus.src.core.methods import linearized_fuzzy_c_medoids
from clus.src.core.methods import linearized_fuzzy_c_medoids_select


ALIASES_KMEANS = ("kmeans",)
ALIASES_FUZZY_C_MEANS = ("fuzzy_c_means", "fcm")
ALIASES_POSSIBILISTIC_C_MEANS = ("possibilistic_c_means", "pcm")
ALIASES_FUZZY_C_MEDOIDS = ("fuzzy_c_medoids", "fcmdd")
ALIASES_HARD_C_MEDOIDS = ("hard_c_medoids", "hcmdd")
ALIASES_LINEARIZED_FUZZY_C_MEDOIDS = ("linearized_fuzzy_c_medoids", "lfcmdd", "l_fc_med")
ALIASES_LINEARIZED_FUZZY_C_MEDOIDS_SELECT = ("linearized_fuzzy_c_medoids_select", "l_fcmed_select")
ALIASES_DATASTREAM_LINEARIZED_FUZZY_C_MEDOIDS_SELECT = ("datastream_linearized_fuzzy_c_medoids_select",
                                                        "ds_lfcmed_select")


class UnknownClusteringMethods(Exception):
    def __init__(self, method_name: str):
        Exception.__init__(self, "The clustering method : \"{method_name}\" doesn't exists".format(
            method_name=method_name
        ))


def use_distance_matrix(clustering_method: str) -> bool:
    return clustering_method in list(
        ALIASES_FUZZY_C_MEDOIDS +
        ALIASES_HARD_C_MEDOIDS +
        ALIASES_LINEARIZED_FUZZY_C_MEDOIDS +
        ALIASES_LINEARIZED_FUZZY_C_MEDOIDS_SELECT +
        ALIASES_DATASTREAM_LINEARIZED_FUZZY_C_MEDOIDS_SELECT
    )


def use_medoids(clustering_method: str) -> bool:
    return clustering_method in list(
        ALIASES_FUZZY_C_MEDOIDS +
        ALIASES_HARD_C_MEDOIDS +
        ALIASES_LINEARIZED_FUZZY_C_MEDOIDS +
        ALIASES_LINEARIZED_FUZZY_C_MEDOIDS_SELECT +
        ALIASES_DATASTREAM_LINEARIZED_FUZZY_C_MEDOIDS_SELECT
    )


def get_clustering_function(string: str) -> Callable:
    string = string.lower()
    if string in ALIASES_KMEANS:
        return kmeans
    elif string in ALIASES_FUZZY_C_MEANS:
        return fuzzy_c_means
    elif string in ALIASES_POSSIBILISTIC_C_MEANS:
        raise NotImplementedError()
    elif string in ALIASES_FUZZY_C_MEDOIDS:
        return fuzzy_c_medoids
    elif string in ALIASES_HARD_C_MEDOIDS:
        return hard_c_medoids
    elif string in ALIASES_LINEARIZED_FUZZY_C_MEDOIDS:
        return linearized_fuzzy_c_medoids
    elif string in ALIASES_LINEARIZED_FUZZY_C_MEDOIDS_SELECT:
        return linearized_fuzzy_c_medoids_select
    elif string in ALIASES_DATASTREAM_LINEARIZED_FUZZY_C_MEDOIDS_SELECT:
        raise NotImplementedError()
    else:
        raise UnknownClusteringMethods(string)


if __name__ == "__main__":
    pass