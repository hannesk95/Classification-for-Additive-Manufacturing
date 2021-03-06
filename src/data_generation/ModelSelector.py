import os
import open3d as o3d
from tqdm import tqdm
import numpy as np
import logging


def _get_filesize(input_path: str, max_filesize: float) -> dict:
    """Method for getting the filesize of each file."""

    files = {}
    models = os.listdir(input_path)

    for model in tqdm(iterable=models, desc='INFO - Getting size of files!'):
        if not model.endswith('.stl'):
            continue

        filepath = os.path.join(input_path, model)
        size_in_MByte = ((os.path.getsize(filepath)) / 1000) / 1000

        if max_filesize >= size_in_MByte:
            files[filepath] = size_in_MByte

    # Sort dictionary by value in ascending order
    files = dict(sorted(files.items(), key=lambda item: item[1]))

    return files


def _compute_compactness(mesh: object) -> float:
    """
    Method which calculates the compactness of a given 3D model.
    @param mesh: 3D mesh object which was read in by Open3D
    @return: number which indicated compactness of mesh object
    """

    # TODO: Check metadata in order to calculate compactness for non-watertight models
    # TODO: Get intuition about feasible compactness parameter value

    bounding_box = mesh.get_axis_aligned_bounding_box()
    volume_bb = bounding_box.volume()

    try:
        volume_mesh = mesh.get_volume()
        compactness = volume_mesh / volume_bb
    except RuntimeError as err:
        compactness = None
        print(err)

    return compactness


class ModelSelector:
    """Class for pre-selecting 3D models according to filesize and compactness."""

    def __init__(self, input_path: str = None, max_filesize: float = None,
                 min_compactness: float = 0.0, num_files: int = 0):
        """
        Constructor method in order to initialize the object.
        @param input_path: Input path to the directory where dataset files are stored.
        @param max_filesize: Maximum filesize of a 3D model in order to be selected (in MegaByte).
        @param min_compactness: Minimum compactness of a 3D model in order to be selected. Range between [0, 1].
        @param num_files: Number of files to be returned.
        """

        self.input_path = input_path
        self.max_filesize = max_filesize
        self.min_compactness = min_compactness
        self.num_files = num_files
        self.check_compactness = True
        self.preselection = {}

        if input_path is None:
            raise ValueError("[ERROR]: Path to the dataset containing the files has to be given!")

        if max_filesize is None:
            raise ValueError("[ERROR]: Please specify maximum filesize!")

        if min_compactness == 0.0:
            # logging.info("Compactness was not specified, continuing without checking compactness!")
            self.check_compactness = False

        if num_files == 0:
            logging.info("Number of files was not specified, return all files which fulfill requirements!")

    def _load_model(self, files: dict, min_compactness: float) -> dict:
        """Method for loading the models."""

        filepaths = list(files.keys())

        for file in tqdm(iterable=filepaths, desc='[INFO]: Calculate compactness of files!'):
            mesh = o3d.io.read_triangle_mesh(file)
            mesh.scale(1 / np.max(mesh.get_max_bound() - mesh.get_min_bound()), center=mesh.get_center())
            mesh_compactness = _compute_compactness(mesh)

            if mesh_compactness < min_compactness or mesh_compactness is None:
                del files[file]

        return files

    def select_models(self) -> list:
        """
        Method which returns a list of preselected files according to maximum filesize
        and minimum compactness (if specified).
        @return: list of selected files according to filesize and compactness
        """
        self.preselection = _get_filesize(self.input_path, self.max_filesize)

        if self.check_compactness:
            self.preselection = self._load_model(self.preselection.copy(), self.min_compactness)

        if self.num_files != 0 and self.num_files < len(list(self.preselection.keys())):
            return list(self.preselection.keys())[:self.num_files]
        else:
            return list(self.preselection.keys())
