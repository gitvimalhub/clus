import numpy as np

from sklearn.cluster import DBSCAN

from clus.src.utils.decorator import remove_unexpected_arguments


@remove_unexpected_arguments
def dbscan(data, eps=1e-6, min_samples=3, weights=None):
    assert len(data.shape) == 2, "The data must be a 2D array"
    assert data.shape[0] > 0, "The data must have at least one example"
    assert data.shape[1] > 0, "The data must have at least one feature"
    assert (weights is None) or (len(weights) == data.shape[1]),\
        "The number of weights given must be the same as the number of features. Expected size : %s, given size : %s" %\
        (data.shape[1], len(weights))
    # TODO: assert eps et min_samples

    if weights is not None:
        # Applying weighted euclidean distance is equivalent to applying traditional euclidean distance into data
        # weighted by the square root of the weights, see [5]
        data = data * np.sqrt(weights)

    clustering = DBSCAN(eps=eps, min_samples=min_samples, n_jobs=-1).fit(data)

    return {
        "affectations": clustering.labels_,
        "number_of_clusters": np.unique(clustering.labels_).size
    }


if __name__ == "__main__":
    pass
