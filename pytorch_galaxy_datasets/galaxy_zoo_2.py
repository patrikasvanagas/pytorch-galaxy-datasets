from nis import cat
import os
import logging

import pandas as pd
from urllib.error import URLError
from torchvision.datasets.utils import download_and_extract_archive

from pytorch_galaxy_datasets import galaxy_datamodule, galaxy_dataset

# TODO could eventually refactor this out of Zoobot as well
from zoobot.shared import label_metadata


class GZ2DataModule(galaxy_datamodule.GalaxyDataModule):

    def __init__(self, *args, **kwargs) -> None:
        """
        Currently identical to GalaxyDataModule - see that description
        """
        super().__init__(*args, **kwargs)

    def prepare_data(self):
        GZ2Dataset(self.data_dir, download=True)


# https://pytorch.org/vision/stable/_modules/torchvision/datasets/mnist.html for download process inspiration
class GZ2Dataset(galaxy_dataset.GalaxyDataset):

    def __init__(self, data_dir, catalog=None, label_cols=None, download=False, transform=None, target_transform=None, album=True) -> None:

        # can use target_transform to turn counts into regression or even classification
        # will need another step to drop rows, in DataModule probably

        self.data_dir = data_dir
        self.image_dir = os.path.join(self.data_dir, 'images')

        self.resources = [
            # ('https://drive.google.com/uc?export=download&id=1pz3Tyfd6snLhcRonMh6V6qjZ7gjozJbO', '9d73da0d58f48e44e1ac13dce0232c98'),  # the catalog
            ('https://zenodo.org/record/3565489/files/images_gz2.zip',
             'bc647032d31e50c798770cf4430525c7')  # the images
        ]

        if download:
            self.download()

        if not self._check_exists():
            raise RuntimeError(
                "Dataset not found. You can use download=True to download it")

        if catalog is None:
            logging.info('Loading GZ2 dataset with default (unsplit) catalog')
            # catalog = pd.read_parquet(os.path.join(data_dir, 'catalog.parquet'))  # TODO override for now
            catalog = pd.read_parquet(
                '/nvme1/scratch/walml/repos/curation-datasets/gz2_downloadable_catalog.parquet')
            catalog['file_loc'] = catalog['filename'].apply(
                lambda x: os.path.join(self.image_dir, x))
        else:
            logging.info(
                'Overriding GZ2 default catalog with user-provided catalog (length {})'.format(len(catalog)))
            assert isinstance(catalog, pd.DataFrame)
            # will always check label_cols as well, below
            assert 'file_loc' in catalog.columns.values

        if label_cols is None:
            logging.info('Loading GZ2 dataset with default label columns')
            label_cols = label_metadata.gz2_label_cols
        else:
            logging.warning(
                'User provided GZ2 dataset with custom label cols - be careful!')
        assert all([col in catalog.columns.values for col in label_cols])

        super().__init__(catalog=catalog, label_cols=label_cols,
                         transform=transform, target_transform=target_transform, album=album)

    def download(self) -> None:
        """Download the data if it doesn't exist already."""

        if self._check_exists():
            return

        os.makedirs(self.data_dir, exist_ok=True)

        # download files
        for url, md5 in self.resources:
            filename = os.path.basename(url)
            try:
                print(f"Downloading {url}")
                download_and_extract_archive(
                    url, download_root=self.data_dir, filename=filename, md5=md5)
            except URLError as error:
                print(f"Failed to download (trying next):\n{error}")
                continue
            finally:
                print()  # not sure what this achieves, copied from mnist.py
            break
        else:
            raise RuntimeError(f"Error downloading {filename}")

    def _check_exists(self) -> bool:

        return all([
            os.path.isdir(self.image_dir),
            os.path.isfile(os.path.join(self.image_dir, '100097.jpg')),
            # os.path.isfile(os.path.join(self.image_dir, '26603.jpg'))  # TODO should check first and last and a few others
            # TODO add catalog
        ])


if __name__ == '__main__':

    dataset = GZ2Dataset(
        data_dir='/nvme1/scratch/walml/repos/pytorch-galaxy-datasets/tests/gz2_root',
        download=True
    )

    for image, label in dataset:
        print(image.shape, label)
        break

    data_dir = '/nvme1/scratch/walml/repos/pytorch-galaxy-datasets/tests/gz2_root'
    catalog = pd.read_parquet(
        '/nvme1/scratch/walml/repos/curation-datasets/gz2_downloadable_catalog.parquet')
    catalog['file_loc'] = catalog['filename'].apply(
        lambda x: os.path.join(data_dir, 'images', x))

    datamodule = GZ2DataModule(
        dataset_class=GZ2Dataset,
        data_dir=data_dir,
        catalog=catalog,
    )

    datamodule.prepare_data()
    datamodule.setup()

    for images, labels in datamodule.train_dataloader():
        print(images.shape, labels.shape)
        break