from collections import namedtuple
from datetime import datetime
import logging
import os

from storage import util
from storage import columns

logger = logging.getLogger(__name__)

_IMAGE_TSV_COLUMNS = [
    # The order of this list maps to the order of the columns in the TSV.
    columns.StringColumn(
        name='foreign_identifier',  required=False, size=3000, truncate=False
    ),
    columns.URLColumn(
        name='foreign_landing_url', required=True,  size=1000
    ),
    columns.URLColumn(
        # `url` in DB
        name='image_url',           required=True,  size=3000
    ),
    columns.URLColumn(
        # `thumbnail` in DB
        name='thumbnail_url',       required=False, size=3000
    ),
    columns.IntegerColumn(
        name='width',               required=False
    ),
    columns.IntegerColumn(
        name='height',              required=False
    ),
    columns.IntegerColumn(
        name='filesize',            required=False
    ),
    columns.StringColumn(
        name='license_',            required=True,  size=50,   truncate=False
    ),
    columns.StringColumn(
        name='license_version',     required=True,  size=25,   truncate=False
    ),
    columns.StringColumn(
        name='creator',             required=False, size=2000, truncate=True
    ),
    columns.URLColumn(
        name='creator_url',         required=False, size=2000
    ),
    columns.StringColumn(
        name='title',               required=False, size=5000, truncate=True
    ),
    columns.JSONColumn(
        name='meta_data',           required=False
    ),
    columns.JSONColumn(
        name='tags',                required=False
    ),
    columns.BooleanColumn(
        name='watermarked',         required=False
    ),
    columns.StringColumn(
        name='provider',            required=False, size=80,   truncate=False
    ),
    columns.StringColumn(
        name='source',              required=False, size=80,   truncate=False
    )
]


_Image = namedtuple(
    '_Image',
    [c.NAME for c in _IMAGE_TSV_COLUMNS]
)


class ImageStore:
    """
    A class that stores image information from a given provider.

    Optional init arguments:
    provider:       String marking the provider in the `image` table of the DB.
    output_file:    String giving a temporary .tsv filename (*not* the
                    full path) where the image info should be stored.
    output_dir:     String giving a path where `output_file` should be placed.
    buffer_length:  Integer giving the maximum number of image information rows
                    to store in memory before writing them to disk.
    """

    def __init__(
            self,
            provider=None,
            output_file=None,
            output_dir=None,
            buffer_length=100
    ):
        logger.info('Initialized with provider {}'.format(provider))
        self._image_buffer = []
        self._total_images = 0
        self._PROVIDER = provider
        self._BUFFER_LENGTH = buffer_length
        self._NOW = datetime.now()
        self._OUTPUT_PATH = self._initialize_output_path(
            output_dir,
            output_file,
            provider,
        )

    def _initialize_output_path(self, output_dir, output_file, provider):
        if output_dir is None:
            logger.info(
                'No given output directory.  '
                'Using OUTPUT_DIR from environment.'
            )
            output_dir = os.getenv('OUTPUT_DIR')
        if output_dir is None:
            logger.warning(
                'OUTPUT_DIR is not set in the enivronment.  '
                'Output will go to /tmp.'
            )
            output_dir = '/tmp'

        if output_file is not None:
            output_file = str(output_file)
        else:
            output_file = '{}_{}.tsv'.format(
                provider, datetime.strftime(self._NOW, '%Y%m%d%H%M%S')
            )

        output_path = os.path.join(output_dir, output_file)
        logger.info('Output path: {}'.format(output_path))
        return output_path

    def add_item(
            self,
            foreign_landing_url=None,
            image_url=None,
            thumbnail_url=None,
            license_url=None,
            license_=None,
            license_version=None,
            foreign_identifier=None,
            width=None,
            height=None,
            creator=None,
            creator_url=None,
            title=None,
            meta_data=None,
            raw_tags=None,
            watermarked='f',
            source=None
    ):
        """
        Add information for a single image to the ImageStore.

        Required Arguments:

        foreign_landing_url:  URL of page where the image lives on the
                              source website.
        image_url:            Direct link to the image file

        Semi-Required Arguments

        license_url:      URL of the license for the image on the
                          Creative Commons website.
        license_:         String representation of a Creative Commons
                          license.  For valid options, see
                          `storage.constants.LICENSE_PATH_MAP`
        license_version:  Version of the given license.

        Note on license arguments: These are 'semi-required' in that
        either a valid `license_url` must be given, or a valid
        `license_`, `license_version` pair must be given. Otherwise, the
        image data will be discarded.

        Optional Arguments:

        thumbnail_url:       Direct link to a thumbnail-sized version of
                             the image
        foreign_identifier:  Unique identifier for the image on the
                             source site.
        width:               in pixels
        height:              in pixels
        creator:             The creator of the image.
        creator_url:         The user page, or home page of the creator.
        title:               Title of the image.
        meta_data:           Dictionary of meta_data about the image.
                             Currently, a key that we prefer to have is
                             `description`. If 'license_url' is included
                             in this dictionary, and `license_url` is
                             given as an argument, the argument will
                             replace the one given in the dictionary.
        raw_tags:            List of tags associated with the image
        watermarked:         A boolean, or 't' or 'f' string; whether or
                             not the image has a noticeable watermark.
        source:              If different from the provider.  This might
                             be the case when we get information from
                             some aggregation of images.  In this case,
                             the `source` argument gives the aggregator,
                             and the `provider` argument in the
                             ImageStore init function is the specific
                             provider of the image.
        """
        image = self._get_image(
                foreign_landing_url=foreign_landing_url,
                image_url=image_url,
                thumbnail_url=thumbnail_url,
                license_url=license_url,
                license_=license_,
                license_version=license_version,
                foreign_identifier=foreign_identifier,
                width=width,
                height=height,
                creator=creator,
                creator_url=creator_url,
                title=title,
                meta_data=meta_data,
                raw_tags=raw_tags,
                watermarked=watermarked,
                source=source
            )
        tsv_row = self._create_tsv_row(image)
        if tsv_row:
            self._image_buffer.append(tsv_row)
        if len(self._image_buffer) >= self._BUFFER_LENGTH:
            self._flush_buffer()

        return self._total_images

    def commit(self):
        """Writes all remaining images in the buffer to disk."""
        self._flush_buffer()

        return self._total_images

    def _get_image(
            self,
            foreign_identifier,
            foreign_landing_url,
            image_url,
            thumbnail_url,
            width,
            height,
            license_url,
            license_,
            license_version,
            creator,
            creator_url,
            title,
            meta_data,
            raw_tags,
            watermarked,
            source,
    ):
        license_, license_version = util.choose_license_and_version(
            license_url=license_url,
            license_=license_,
            license_version=license_version
        )
        source = util.get_source(source, self._PROVIDER)
        meta_data = self._enrich_meta_data(
            meta_data,
            license_url=license_url
        )
        tags = self._enrich_tags(raw_tags)

        return _Image(
                foreign_identifier=foreign_identifier,
                foreign_landing_url=foreign_landing_url,
                image_url=image_url,
                thumbnail_url=thumbnail_url,
                license_=license_,
                license_version=license_version,
                width=width,
                height=height,
                filesize=None,
                creator=creator,
                creator_url=creator_url,
                title=title,
                meta_data=meta_data,
                tags=tags,
                watermarked=watermarked,
                provider=self._PROVIDER,
                source=source
            )

    def _create_tsv_row(
            self,
            image,
            columns=_IMAGE_TSV_COLUMNS
    ):
        row_length = len(columns)
        prepared_strings = [
            columns[i].prepare_string(image[i]) for i in range(row_length)
        ]
        logger.debug('Prepared strings list:\n{}'.format(prepared_strings))
        for i in range(row_length):
            if columns[i].REQUIRED and prepared_strings[i] is None:
                return None
        else:
            return '\t'.join(
                [s if s is not None else '\\N' for s in prepared_strings]
            ) + '\n'

    def _flush_buffer(self):
        buffer_length = len(self._image_buffer)
        if buffer_length > 0:
            logger.debug(
                'Writing {} lines from buffer to disk.'
                .format(buffer_length)
            )
            with open(self._OUTPUT_PATH, 'a') as f:
                f.writelines(self._image_buffer)
                self._image_buffer = []
                self._total_images += buffer_length
                logger.debug(
                    'Total Images Processed so far:  {}'
                    .format(self._total_images)
                )
        else:
            logger.debug('Empty buffer!  Nothing to write.')
        return buffer_length

    def _enrich_meta_data(self, meta_data, license_url):
        if type(meta_data) != dict:
            logger.debug(
                '`meta_data` is not a dictionary: {}'.format(meta_data)
            )
            enriched_meta_data = {'license_url': license_url}
        else:
            enriched_meta_data = meta_data
            enriched_meta_data.update(license_url=license_url)
        return enriched_meta_data

    def _enrich_tags(self, raw_tags):
        if type(raw_tags) != list:
            logger.debug('`tags` is not a list.')
            return None
        else:
            return [
                self._format_raw_tag(tag) for tag in raw_tags
            ]

    def _format_raw_tag(self, tag):
        if type(tag) == dict and tag.get('name') and tag.get('provider'):
            logger.debug('Tag already enriched: {}'.format(tag))
            return tag
        else:
            logger.debug('Enriching tag: {}'.format(tag))
            return {'name': tag, 'provider': self._PROVIDER}
