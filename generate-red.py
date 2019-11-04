#!/usr/bin/env python3

import os
from argparse import ArgumentParser

from ruamel.yaml import YAML


yaml = YAML(typ='safe')


CAMELYON_UTILS_IMAGE = 'docker.io/deepprojects/camelyon-utils:0.5'
CAMELYON_CNN_IMAGE = 'docker.io/deepprojects/camelyon-cnn:0.1.1'


parser = ArgumentParser(description='Generate RED files of CAMELYON16 Experiments V2.')
parser.add_argument(
    'ssh_host', action='store', type=str, metavar='HOST',
    help='HOST name of SSH server with appropriate storage space to upload experiment results.'
)
parser.add_argument(
    '--cc-agency-url', action='store', type=str, metavar='URL',
    help='URL to CC-Agency instance, that is used as RED execution engine. Default: cc-faice is used as a local RED execution engine.'
)
parser.add_argument(
    '--output-dir', action='store', type=str, metavar='PATH', default='custom',
    help='Directory PATH to store generated RED files. Default: custom'
)
parser.add_argument(
    '--num-tiles', action='store', type=int, metavar='NUM', default=750,
    help='Number of tiles to be selected per slide for merged.hd5 file. Default: 750, reduce number if resources are limited.'
)
parser.add_argument(
    '--tumor-slides-end-index', action='store', type=int, metavar='INDEX', default=161, choices=range(2, 162),
    help='Only tumor slides from index position 1 to this end INDEX (exclusive) will be processed. Default: 161.'
)
parser.add_argument(
    '--normal-slides-end-index', action='store', type=int, metavar='INDEX', default=161, choices=range(2, 162),
    help='Only normal slides from index position 1 to this end INDEX (exclusive) will be processed. Default: 161.'
)
args = parser.parse_args()


if not os.path.exists(args.output_dir):
    os.makedirs(args.output_dir)


with open('slide-to-tiles.cwl.yml') as f:
    slide_to_tiles_cli = yaml.load(f)

with open('merge-tiles.cwl.yml') as f:
    merge_tiles_cli = yaml.load(f)

with open('cnn-trainings.cwl.yml') as f:
    cnn_training_cli = yaml.load(f)


execution_ccfaice = {
    'engine': 'ccfaice',
    'settings': {}
}

# generate slide-to-tiles.red.yml

# select tiles from highest resolution in WSI, pixel_spacing is a unified scaling accross scanners
pixel_spacing = 0.0002439
ssh_experiments_dir = 'camelyon-experiments-v2'
ssh_tiles_dir = '{}/tiles'.format(ssh_experiments_dir)
ftp_camelyon_url = 'ftp://parrot.genomics.cn/gigadb/pub/10.5524/100001_101000/100439/CAMELYON16/training/'


batches = []

index = range(1, args.tumor_slides_end_index)

for i in index:
    batch = {
        'inputs': {
            'pixel_spacing': pixel_spacing,
            'slide': {
                'class': 'File',
                'connector': {
                    'command': 'red-connector-ftp',
                    'access': {
                        'url': '{}/tumor/tumor_{:03d}.tif'.format(ftp_camelyon_url, i)
                    }
                }
            },
            'mask_dir': {
                'class': 'Directory',
                'connector': {
                    'command': 'red-connector-ftp-archive',
                    'access': {
                        'url': '{}/lesion_annotations.zip'.format(ftp_camelyon_url),
                        'archiveFormat': 'zip'
                    }
                }
            },
            'mask': 'tumor_{:03d}.xml'.format(i)
        },
        'outputs': {
            'tiles': {
                'class': 'File',
                'connector': {
                    'command': 'red-connector-ssh',
                    'access': {
                        'host': args.ssh_host,
                        'auth': {
                            'username': '{{ssh_username}}',
                            'password': '{{ssh_password}}'
                        },
                        'filePath': '{}/tumor_{:03d}.hdf5'.format(ssh_tiles_dir, i)
                    }
                }
            }
        }
    }
    batches.append(batch)


# normal_086.tif does not exist in dataset
# normal_144.tif cannot be processed
index = [i for i in range(1, args.normal_slides_end_index) if i not in [86, 144]]

for i in index:
    batch = {
        'inputs': {
            'pixel_spacing': pixel_spacing,
            'slide': {
                'class': 'File',
                'connector': {
                    'command': 'red-connector-ftp',
                    'access': {
                        'url': '{}/normal/normal_{:03d}.tif'.format(ftp_camelyon_url, i)
                    }
                }
            },
        },
        'outputs': {
            'tiles': {
                'class': 'File',
                'connector': {
                    'command': 'red-connector-ssh',
                    'access': {
                        'host': args.ssh_host,
                        'auth': {
                            'username': '{{ssh_username}}',
                            'password': '{{ssh_password}}'
                        },
                        'filePath': '{}/normal_{:03d}.hdf5'.format(ssh_tiles_dir, i)
                    }
                }
            }
        }
    }
    batches.append(batch)

execution = execution_ccfaice

if args.cc_agency_url:
    execution = {
        'engine': 'ccagency',
        'settings': {
            'access': {
                'url': args.cc_agency_url,
                'auth': {
                    'username': '{{agency_username}}',
                    'password': '{{agency_password}}'
                }
            },
            'retryIfFailed': True,
            'batchConcurrencyLimit': 16
        }
    }

red = {
    'redVersion': '8',
    'cli': slide_to_tiles_cli,
    'batches': batches,
    'container': {
        'engine': 'docker',
        'settings': {
            'image': {
                'url': CAMELYON_UTILS_IMAGE
            },
            'ram': 8192
        }
    },
    'execution': execution
}

red_path = 'slide-to-tiles.red.yml'
if args.output_dir:
    red_path = os.path.join(args.output_dir, red_path)

with open(red_path, 'w') as f:
    yaml.dump(red, f)


# generate merge-tiles.red.yml
ssh_merged_dir = '{}/merged'.format(ssh_experiments_dir)

execution = execution_ccfaice

if args.cc_agency_url:
    execution = {
        'engine': 'ccagency',
        'settings': {
            'access': {
                'url': args.cc_agency_url,
                'auth': {
                    'username': '{{agency_username}}',
                    'password': '{{agency_password}}'
                }
            },
            'retryIfFailed': True
        }
    }

red = {
    'redVersion': '8',
    'cli': merge_tiles_cli,
    'inputs': {
        'indir': {
            'class': 'Directory',
            'connector': {
                'command': 'red-connector-ssh',
                'access': {
                    'host': args.ssh_host,
                    'auth': {
                        'username': '{{ssh_username}}',
                        'password': '{{ssh_password}}'
                    },
                    'filePath': ssh_tiles_dir
                }
            }
        },
        'outdir': {
            'class': 'Directory',
            'connector': {
                'command': 'red-connector-ssh',
                'access': {
                    'host': args.ssh_host,
                    'auth': {
                        'username': '{{ssh_username}}',
                        'password': '{{ssh_password}}'
                    },
                    'filePath': ssh_tiles_dir
                }
            }
        },
        'numtiles': args.num_tiles
    },
    'outputs': {},
    'container': {
        'engine': 'docker',
        'settings': {
            'image': {
                'url': CAMELYON_UTILS_IMAGE
            },
            'ram': 8192
        }
    },
    'execution': execution
}

red_path = 'merge-tiles.red.yml'
if args.output_dir:
    red_path = os.path.join(args.output_dir, red_path)

with open(red_path, 'w') as f:
    yaml.dump(red, f)
