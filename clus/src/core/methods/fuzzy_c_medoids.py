import scipy

import numpy as np
from scipy.spatial.distance import cdist
from tqdm import tqdm

from clus.src.core.analysis import ambiguity, partition_coefficient, partition_entropy
from clus.src.core.cluster_initialization import cluster_initialization
from clus.src.core.handle_empty_clusters import handle_empty_clusters
from clus.src.utils.decorator import remove_unexpected_arguments
from clus.src.utils.array import square_idx_to_condensed_idx

_FORMAT_PROGRESS_BAR = r"{n_fmt}/{total_fmt} max_iter, elapsed:{elapsed}, ETA:{remaining}{postfix}"


@remove_unexpected_arguments
def fuzzy_c_medoids(data, distance_matrix, components=10, eps=1e-4,
                    max_iter=1000, fuzzifier=2, initialization_method="random_choice",
                    empty_clusters_method="nothing",
                    medoids_idx=None):
    """ Performs the fuzzy c-medoids clustering algorithm on a dataset.

    :param data: The dataset into which the clustering will be performed. The dataset must be 2D np.array with rows as
    examples and columns as features.
    :param distance_matrix: The pairwise distance matrix applied across all examples from the data matrix. The distance
    matrix must be encoded into a condensed distance vector (see:
    https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.distance.squareform.html)
    :param components: The number of components (clusters) wanted.
    :param eps: Criterion used to define convergence. If the absolute differences between two consecutive losses is
    lower than `eps`, the clustering stop.
    :param max_iter: Criterion used to stop the clustering if the number of iterations exceeds `max_iter`.
    :param fuzzifier: Membership fuzzification coefficient.
    :param initialization_method: Method used to initialise the centroids. Can take one of the following values :
    * "random_uniform" or "uniform", samples values between the min and max across each dimension.
    * "random_gaussian" or "gaussian", samples values from a gaussian with the same mean and std as each data's
    dimension.
    * "random_choice" or "choice", samples random examples from the data without replacement.
    * "central_dissimilar_medoids", sample the first medoid as the most central point of the dataset, then sample all
    successive medoids as the most dissimilar to all medoids that have already been picked.
    * "central_dissimilar_random_medoids", same as "central_dissimilar_medoids", but the first medoid is sampled
    randomly.
    :param empty_clusters_method: Method used at each iteration to handle empty clusters. Can take one of the following
    values :
    * "nothing", do absolutely nothing and ignore empty clusters.
    * "random_example", assign a random example to all empty clusters.
    * "furthest_example_from_its_centroid", assign the furthest example from its centroid to each empty cluster.
    :param medoids_idx: Initials medoids indexes to use instead of randomly initialize them.
    :return: A tuple containing :
    * The memberships matrix.
    * The medoids matrix.
    * An array with all losses at each iteration.
    """
    assert len(data.shape) == 2, "The data must be a 2D array"
    assert data.shape[0] > 0, "The data must have at least one example"
    assert data.shape[1] > 0, "The data must have at least one feature"
    assert (distance_matrix.shape[0] == distance_matrix.shape[1] == data.shape[0]) or (scipy.spatial.distance.is_valid_y(distance_matrix)), "The distance matrix is not encoded into a condensed distance vector, nor is a square distance matrix"
    assert 1 <= components <= data.shape[0], "The number of components wanted must be between 1 and %s" % data.shape[0]
    assert 0 <= max_iter, "The number of max iterations must be positive"
    assert fuzzifier > 1, "The fuzzifier must be greater than 1"
    assert (medoids_idx is None) or (medoids_idx.shape == components), \
        "The given medoids indexes do not have a correct shape. Expected shape : {}, given shape : {}".format(
            (components,), medoids_idx.shape
    )
    assert (medoids_idx is None) or np.all(medoids_idx < data.shape[0]), \
        "The provided medoid indexes array contains unreachable indexes"

    # Initialisation
    if medoids_idx is None:
        medoids_idx = cluster_initialization(data, components, initialization_method, need_idx=True)

    if distance_matrix.shape[0] == distance_matrix.shape[1]:
        # The distance matrix is a squared distance matrix, apply usual methods
        _compute_memberships = _compute_memberships_square
        _compute_medoids = _compute_medoids_square
        _compute_loss = _compute_loss_square
    else:
        # The distance matrix is a condensed distance matrix.
        # Indexing is different, thus use other methods
        medoids_idx = square_idx_to_condensed_idx(medoids_idx, data.shape[0])
        _compute_memberships = _compute_memberships_condensed
        _compute_medoids = _compute_medoids_condensed
        _compute_loss = _compute_loss_condensed

    with tqdm(total=max_iter, bar_format=_FORMAT_PROGRESS_BAR) as progress_bar:
        best_memberships = None
        best_medoids_idx = None
        best_loss = np.inf

        memberships = None
        losses = []
        current_iter = 0
        while (current_iter < max_iter) and \
                ((current_iter < 2) or not (abs(losses[-1] - losses[-2]) <= eps)):
            # Compute memberships
            memberships = _compute_memberships(distance_matrix, medoids_idx, fuzzifier)
            handle_empty_clusters(distance_matrix, medoids_idx, memberships, strategy=empty_clusters_method)

            # Compute medoids
            medoids_idx = _compute_medoids(distance_matrix, memberships, fuzzifier)

            # Compute loss
            loss = _compute_loss(distance_matrix, medoids_idx, memberships, fuzzifier)
            losses.append(loss)
            if loss < best_loss:
                best_loss = loss
                best_memberships = memberships
                best_medoids_idx = medoids_idx

            # Update the progress bar
            current_iter += 1
            progress_bar.update()
            progress_bar.set_postfix({
                "Loss": "{0:.6f}".format(loss),
                "best_loss": "{0:.6f}".format(best_loss)
            })

    return {
        "memberships": best_memberships,
        "medoids_indexes": best_medoids_idx,
        "clusters_center": data[best_medoids_idx, :],
        "losses": np.array(losses),
        "affectations": best_memberships.argmax(axis=1),
        "ambiguity": ambiguity(best_memberships),
        "partition_coefficient": partition_coefficient(best_memberships),
        "partition_entropy": partition_entropy(best_memberships),
    }


def _compute_memberships_square(distance_matrix, medoids_idx, fuzzifier):
    dist_data_medoids = distance_matrix[:, medoids_idx]

    # If two examples are of equals distance, the computation will make
    # divisions by zero. We add this small coefficient to not divide by zero
    # while keeping our distances as correct as possible
    dist_data_medoids += np.fmax(dist_data_medoids, np.finfo(distance_matrix.dtype).eps)

    tmp = (1 / dist_data_medoids) ** (1 / (fuzzifier - 1))
    memberships = tmp / tmp.sum(axis=1, keepdims=True)

    for index_medoid, medoid in enumerate(medoids_idx):
        memberships[medoid, :] = 0.
        memberships[medoid, index_medoid] = 1.

    return memberships


def _compute_medoids_square(distance_matrix, memberships, fuzzifier):
    fuzzified_memberships = memberships ** fuzzifier
    iterable = ((distance_matrix * fuzzified_memberships[:, i]).sum(1).argmin(0) for i in range(memberships.shape[1]))
    return np.fromiter(iterable, count=memberships.shape[1], dtype=np.int64)


def _compute_loss_square(distance_matrix, medoids_idx, memberships, fuzzifier):
    dist_data_centroids = distance_matrix[:, medoids_idx]
    return ((memberships ** fuzzifier) * dist_data_centroids).sum()


def _compute_memberships_condensed(distance_matrix, medoids_idx, fuzzifier):
    dist_data_medoids = distance_matrix[medoids_idx]
    print(medoids_idx)
    print(dist_data_medoids)

    # If two examples are of equals distance, the computation will make
    # divisions by zero. We add this small coefficient to not divide by zero
    # while keeping our distances as correct as possible
    dist_data_medoids += np.fmax(dist_data_medoids, np.finfo(distance_matrix.dtype).eps)

    tmp = (1 / dist_data_medoids) ** (1 / (fuzzifier - 1))
    memberships = tmp / tmp.sum(axis=0, keepdims=True)
    print(memberships)

    for index_medoid, medoid in enumerate(medoids_idx):
        memberships[medoid, :] = 0.
        memberships[medoid, index_medoid] = 1.

    return memberships


def _compute_medoids_condensed(distance_matrix, memberships, fuzzifier):
    fuzzified_memberships = memberships ** fuzzifier
    iterable = ((distance_matrix * fuzzified_memberships[:, i]).sum(1).argmin(0) for i in range(memberships.shape[1]))
    return np.fromiter(iterable, count=memberships.shape[1], dtype=np.int64)


def _compute_loss_condensed(distance_matrix, medoids_idx, memberships, fuzzifier):
    dist_data_centroids = distance_matrix[:, medoids_idx]
    return ((memberships ** fuzzifier) * dist_data_centroids).sum()


def __compute_memberships_square(distance_matrix, medoids_idx, fuzzifier):
    """ DEPRECATED: old method used to compute the medoids.
    The distance matrix is now in a condensed distance vector form.
    """
    u = np.zeros((distance_matrix.shape[0], medoids_idx.shape[0]))

    for i in range(distance_matrix.shape[0]):
        if i in medoids_idx:
            u[i, :] = 0
            u[i, np.where(medoids_idx == i)[0]] = 1
            continue

        for idx_j, j in enumerate(medoids_idx):
            if np.isclose(distance_matrix[i, j], 0.):
                u[i, :] = 0
                u[i, idx_j] = 1
                break

            top = (1 / (distance_matrix[i, j])) ** (1 / (fuzzifier - 1))

            if np.any(np.isclose(distance_matrix[i, medoids_idx], 0)):
                bottom = 1
            else:
                bottom = sum((1 / (distance_matrix[i, k])) ** (1 / (fuzzifier - 1)) for k in medoids_idx)
            u[i, idx_j] = top / bottom
    return u


def __compute_medoids_square(distance_matrix, memberships, fuzzifier):
    """ DEPRECATED: old method used to compute the medoids.
    Very memory-heavy and slower than the existing method.
    """
    fuzzified_memberships = memberships ** fuzzifier
    return (distance_matrix[..., np.newaxis] * fuzzified_memberships).sum(axis=1).argmin(axis=0)


def __compute_loss_square(distance_matrix, medoids_idx, memberships, fuzzifier):
    """ DEPRECATED: old method used to compute the loss.
    Much slower than the existing method.
    """
    res = 0
    n = distance_matrix.shape[0]

    for idx_medoid, medoid in enumerate(medoids_idx):
        for i in range(n):
            dist = distance_matrix[i, medoid]
            res += (memberships[i][idx_medoid] ** fuzzifier) * dist
    return res


if __name__ == '__main__':
    pass
