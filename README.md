# CAMELYON Experiments V2

CAMELYON Experiments V2 is an improved and merged version of the previously published [camelyon-slide-to-tiles-experiments](https://github.com/deep-projects/camelyon-slide-to-tiles-experiments) and [camelyon-cnns-training-experiments](https://github.com/deep-projects/camelyon-cnns-training-experiments).
This version is easier to reproduce and more concise, than the original experiments and has been updated for RED version 8.

This image processing and deep learning pipeline is fully implement as three subsequent experiments in the Reprodcuble Experiment Description (RED) format.
The experiments can be processed using RED Execution Engines from the [Curious Containers](https://www.curious-containers.cc/) project.

* slide-to-tiles downloads Whole Slide Images (WSI) from the CAMELYON16 dataset via FTP, extracts a certain number of small tiles from the slides and stores the tiles in one HDF5 file per slide.
* merge-tiles loads a certain number of random tiles from the previously generated HDF5 files and stores them in one large array in a single HDF5 file.
* cnn-training loads select random batch slices from the merged tiles to train a CNN for tumor classification.

In the original experiment, the complete CAMELYON16 training data set is downloaded and the merge step produces a very large (1.8 TB) tiles file.
Additionally, the original experiment is executed in the cluster infrastructure of [CBMI - HTW Berlin](https://cbmi.htw-berlin.de/).
This improved version of the experiment can be easily adapted to use less resources and does not require access to CBMI resources, as long as the user can provide an SSH server with appriate storage space for intermediate and final results.
The `generate-red.py` script provides convenient parameters to generate custom RED files.

## Resources

These experiments have been built from the following resources.

* Software package: [camelyon-utils 0.5](https://github.com/deep-projects/camelyon-utils/releases/tag/0.5)
* Docker image: [docker.io/deepprojects/camelyon-utils:0.5](https://cloud.docker.com/u/deepprojects/repository/docker/deepprojects/camelyon-utils) ([Dockerfile](https://github.com/deep-projects/appliances/tree/master/camelyon-utils/0.5))
* Software package: [camelyon-cnns 0.2](https://github.com/deep-projects/camelyon-utils)
* Docker image: [docker.io/deepprojects/camelyon-cnns:0.2](https://cloud.docker.com/u/deepprojects/repository/docker/deepprojects/camelyon-cnns) ([Dockerfile](https://github.com/deep-projects/appliances/tree/master/camelyon-cnns/0.2))
* Docker image with CUDA GPU support: [docker.io/deepprojects/camelyon-cnns:0.2-gpu](https://cloud.docker.com/u/deepprojects/repository/docker/deepprojects/camelyon-cnns) ([Dockerfile](https://github.com/deep-projects/appliances/tree/master/camelyon-cnns/0.2-gpu))


## Reproduce

The full experiments, that require a lot of resources, are located in the `cbmi` directory.
A smaller version of the experiment can generated using the following commands.
A smaller number of data samples and training epochs will result in a lower CNN model quality.

```bash
pip3 install --user -r requirements
./generate-red.py avocado01.f4.htw-berlin.de --cc-agency-url https://agency.f4.htw-berlin.de/cc --output-dir custom --tumor-slides-end-index 4 --normal-slides-end-index 4 --num-tiles 256 --gpus 1 --epochs 1
```

You should provide a different SSH server host name.
CC-Agency is one of two available RED Execution Engines.
If you do not want to setup your own instance of CC-Agency, you can remove the `--cc-agency-url` parameter entirely.
The RED Execution Engine will then be set to `ccfaice` to run experiments on your local Linux host.
This requires Docker to be installed.
For the usage of GPUs you also need *nvidia-container-toolkit* or *nvidia-docker* to be intalled as well.
You can remove the `--gpus` parameter to fall back to CPU processing.
Please note that the CPU version requires more RAM (40 GB).

For more information about the parameters run `./generate-red.py --help`. For more information about Curious Containers we recommend reading the [RED Beginner's Guide](https://www.curious-containers.cc/docs/red-beginners-guide).

To run the generated experiment install the `cc-faice` Python package, that provides the RED client `faice exec` and a local RED execution engine.

```bash
pip3 install --user pipx
pipx install cc-faice==8.*

faice exec custom/slide-to-tiles.red.yml
# wait until succeeded. might be asynchronous with CC-Agency

faice exec custom/merge-tiles.red.yml
# wait until succeeded. might be asynchronous with CC-Agency

faice exec custom/cnn-training-batchConcurrencyLimit-1.red.yml
# wait until succeeded. might be asynchronous with CC-Agency

faice exec custom/cnn-training-batchConcurrencyLimit-3.red.yml
# wait until succeeded. might be asynchronous with CC-Agency

faice exec custom/cnn-training-batchConcurrencyLimit-9.red.yml
# wait until succeeded. might be asynchronous with CC-Agency
```

Each of the three `cnn-training-batchConcurrencyLimit-*.red.yml` contains 9 identical CNN training configurations.
The CNN trainings can be performed with CC-Agency using a certain `batchConcurrencyLimit`, such that 1, 3 or 9 of the 9 runs are executed in parallel.
Depending on the SSH server, that provides the merged tiles via SSHFS into the experiment containers, you might experience a performance impact resulting in different training times.
These training times can be inspected in the log files generated on the SSH server by the experiments.

If the `ccfaice` execution engine is used instead of `ccagency`, there will only be one `cnn-training.red.yml` file, because `ccfaice` does not provide parallel execution and therefore does not have a `batchConcurrencyLimit` setting.
