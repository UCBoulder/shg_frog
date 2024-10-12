from scipy.constants import c as C_MKS


def dist_um_to_T_fs(value_um):
    """
    :param value_um: delta x in micron
    :return value_fs: delta t in femtosecond
    """
    return (2 * value_um / C_MKS) * 1e9


def T_fs_to_dist_um(value_fs):
    """
    :param value_fs: delta t in femtosecond
    :return value_um: delta x in micron
    """
    return (C_MKS * value_fs / 2) * 1e-9
