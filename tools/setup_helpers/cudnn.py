import os
import sys
import glob
from itertools import chain
import re

from .env import check_env_flag
from .cuda import WITH_CUDA, CUDA_HOME


def gather_paths(env_vars):
    return list(chain(*(os.getenv(v, '').split(':') for v in env_vars)))


def find_cudnn_version(cudnn_lib_dir):
    candidate_names = list(glob.glob(os.path.join(cudnn_lib_dir, 'libcudnn*')))
    candidate_names = [os.path.basename(c) for c in candidate_names]

    # suppose version is MAJOR.MINOR.PATCH, all numbers
    version_regex = re.compile('\d+\.\d+\.\d+')
    candidates = [c.group() for c in map(version_regex.search, candidate_names) if c]
    if len(candidates) > 0:
        # normally only one will be retrieved, take the first result
        return candidates[0]

    # if no candidates were found, try MAJOR.MINOR
    version_regex = re.compile('\d+\.\d+')
    candidates = [c.group() for c in map(version_regex.search, candidate_names) if c]
    if len(candidates) > 0:
        return candidates[0]

    # if no candidates were found, try MAJOR
    version_regex = re.compile('\d+')
    candidates = [c.group() for c in map(version_regex.search, candidate_names) if c]
    if len(candidates) > 0:
        return candidates[0]

    return 'unknown'


def check_cudnn_version(cudnn_version_string):
    if cudnn_version_string is 'unknown':
        return  # Assume version is OK and let compilation continue

    cudnn_min_version = 6
    cudnn_version = int(cudnn_version_string.split('.')[0])
    if cudnn_version < cudnn_min_version:
        raise RuntimeError(
            'CuDNN v%s found, but need at least CuDNN v%s. '
            'You can get the latest version of CuDNN from '
            'https://developer.nvidia.com/cudnn' %
            (cudnn_version_string, cudnn_min_version))


is_conda = 'conda' in sys.version or 'Continuum' in sys.version
conda_dir = os.path.join(os.path.dirname(sys.executable), '..')

WITH_CUDNN = False
CUDNN_LIB_DIR = None
CUDNN_INCLUDE_DIR = None
CUDNN_VERSION = None
if WITH_CUDA and not check_env_flag('NO_CUDNN'):
    lib_paths = list(filter(bool, [
        os.getenv('CUDNN_LIB_DIR'),
        os.path.join(CUDA_HOME, 'lib'),
        os.path.join(CUDA_HOME, 'lib64'),
        '/usr/lib/x86_64-linux-gnu/',
        '/usr/lib/powerpc64le-linux-gnu/',
        '/usr/lib/aarch64-linux-gnu/',
    ] + gather_paths([
        'LIBRARY_PATH',
    ]) + gather_paths([
        'LD_LIBRARY_PATH',
    ])))
    include_paths = list(filter(bool, [
        os.getenv('CUDNN_INCLUDE_DIR'),
        os.path.join(CUDA_HOME, 'include'),
        '/usr/include/',
    ] + gather_paths([
        'CPATH',
        'C_INCLUDE_PATH',
        'CPLUS_INCLUDE_PATH',
    ])))
    if is_conda:
        lib_paths.append(os.path.join(conda_dir, 'lib'))
        include_paths.append(os.path.join(conda_dir, 'include'))
    for path in lib_paths:
        if path is None or not os.path.exists(path):
            continue
        if glob.glob(os.path.join(path, 'libcudnn*')):
            CUDNN_LIB_DIR = path
            break
    for path in include_paths:
        if path is None or not os.path.exists(path):
            continue
        if os.path.exists((os.path.join(path, 'cudnn.h'))):
            CUDNN_INCLUDE_DIR = path
            break
    if not CUDNN_LIB_DIR or not CUDNN_INCLUDE_DIR:
        CUDNN_LIB_DIR = CUDNN_INCLUDE_DIR = None
    else:
        CUDNN_VERSION = find_cudnn_version(CUDNN_LIB_DIR)
        check_cudnn_version(CUDNN_VERSION)
        WITH_CUDNN = True
