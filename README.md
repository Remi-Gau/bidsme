# BIDSme

- [The BIDSme workflow](#workflow)
    * [Data preparation](#wf_prep)
    * [Data bidsification](#wf_bids)
    * [Bidsmap configuration](#wf_map)
    * [Plugin configuration](#wf_plug)
- [Examples](#examples)
    * [Dataset 1](#ex1)
- [Supported formats](#formats)
    * [MRI](#mri)
    	+ [hmriNIFTI](#hmriNIFTI)
        + [jsonNIFTI](#jsonNIFTI)
        + [bidsmeNIFTI](#bidsmeNIFTI)
        + [NIFTI](#NIFTI)
        + [DICOM](#dicom)
    * [EEG](#eeg)
        + [BrainVision](#BV)
- [Plug-in functions](#plugins)
- [Implementing additional formats](#new_formats)
- [Bidsmap file structure](#bidsmap)


BIDSme is a user friendly
[open-source](https://gitlab.uliege.be/CyclotronResearchCentre/Public/bidstools/bidsme/bidsme)
python toolkit that converts ("bidsifies") source-level (raw) neuroimaging 
data-sets to [BIDS-conformed](https://bids-specification.readthedocs.io/en/stable).
Rather then depending on complex or ambiguous programmatic logic for the 
identification of imaging modalities, BIDSme uses a direct mapping approach to 
identify and convert the raw source data into BIDS data. The information sources 
that can be used to map the source data to BIDS are retrieved dynamically from 
source data header files (DICOM, BrainVision, nifti etc...) and file source data-set 
file structure (file- and/or directory names, e.g. number of files).

The retrieved information can be modified/adjusted by a set of plugins, 
described [here](#plugins). Plugins can also be used to complete the bidsified 
dataset, for example by parsing log files. 

> NB: BIDSme support variety of formats listed in [supported formats](#formats). 
Additional formats can be implemented following instructions [here](#new_formats).

The mapping information is stored as key-value pairs in the human readable and 
widely supported [YAML](http://yaml.org/) files, generated from a template yaml-file.


## <a name="requirements"></a> Requirements
- python >= 3.6
- pandas
- ruamel.yaml>=0.15.35
- coloredlogs
- pydicom >= 1.4.2
- nibabel >= 3.1.0

## <a name="interface"></a> The BIDSme interface

All interactions with BIDSme occurs from command-line interface, by a master script `bidsme.py`.

This script accepts a small set of parameters and one of the command 

- `prepare` to [prepare dataset](#wf_prep)
- `process` to [process dataset](#wf_process)
- `bidsify` to [bidsify dataset](#wf_bids)
- `map` to [create bidsmap](#wf_map)

Outside the standard `-h`, `-v` options that shows help and version, `bidsme` accepts 
`-c, --configuration` options which takes a path to configuration file. 
This file is searched in (in order) current directory, user-standard directory and 
bids code directory (when available).

The `--conf-save` switch saves the current configuration (affected by command-line
options) in the given location. It is useful to run this option once to update configuration.

> N.B. both `-c` and `--conf-save` must be given **before** the command.

The individual commands accepts common and individual arguments. 
In what follows only common arguments are described, and individual ones are 
described in corresponding sections.

- <a name="gen_cli"></a>Logging options, corresponds to *logging* section of configuration file:
    *  `-q`, `--quiet` suppress the standard output, useful for running in the script
    * `--level` sets the message verbosity of the log output, from very verbose *DEBUG*
    to showing only critical message *CRITICAL*
    * `--formatter` sets the log line format message 
- Plug-in options, corresponds to *plugins* section of configuration file. Affects only
relevant command: 
    * `--plugin` sets the path to plugin file
    * `-o Name=Value` sets the options passed to plugin
- Subject and session selection, corresponds to *selection* section of configuration file
    * `--participants` space separated list of participants to process. Listed participants
    are considered after the bidsification, with `sub-` prefix
    * `--skip-in-tsv` switch that skips participants that already present in destination
    * `--skip-existing` switch that skips participants with corresponding folders existing
    in destination
    * `--skip-existing-sessions` same as above but for sessions
- General options, non existing in configuration file:
    * `--dry-run`, run in the simulation mode, without writing anything outside the
    logs

The full list of commands parameters can be seen using `-h` option:
`bidsme.py [command] -h`.
If a configuration file is set, then the shown default values corresponds to configuration file
parameters.
 

## <a name="workflow"> </a>The BIDSme workflow

The BIDSme workflow is composed in two steps:

  1. [Data preparation](#wf_prep), in which the source dataset is reorganized into standard bids-like structure
  2. [Data bidsification](#wf_bids), in which prepared data is bidsified.

This organisation allow to user intervene before the bidsification in case of 
presence of errors, or to complete the data manually if it could not be completed numerically.

### <a name="wf_prep"></a>Data preparation 

In order to be bidsified, dataset should be put into a form:
```
sub-<subId>/ses-<sesId>/<DataType>/<seriesNo>-<seriesId>/<datafiles>
```
where `subId` and `sesId` are the subject and session label, as defined by BIDS standard. 
`DataType` is an unique label identifying the modality of data, e.g. `EEG` or `MRI`.
`seriesNo` and `seriesId` are the unique identification of given recording series 
which can be defined as a set of recording sharing the same recording parameters 
(e.g. set of 2D slices for same fMRI scan).

A generic data-set can be organized into prepared dataset using `prepare` command.
In addition of parameters cited [above](#gen_cli),
some additional parameters are defined:

- `--part-template` with path to the sidecar json file (template) for future `participant.tsv` file. 
	It is expected to follow the [BIDS-defined structure](https://bids-specification.readthedocs.io/en/stable/02-common-principles.html#tabular-files). 
	It should include **all** needed column descriptions, including the mandatory `participant_id`
- `--sub-prefix` sets the subject prefix in original dataset and can include path. 
	For example if in original dataset subject folders are stored in `participants` folder 
	(`participants/001`, `participants/002` etc.. ), then setting `sub-prefix` to `participants/` 
	(note the slash) will make `prepare` search for subjects in correct folder. 
	The paths can contain wildcard character `*` in case if different participants 
	are stored in different folders (e.g. `patients/001` and `control/002`). Both can be 
	reached by  `--sub-prefix '*/'`. 
	If used, wildcard characters must be protected by single quote in order to avoid shell expansion. 
	The non-path part of prefix is removed from subject id. 
	For this reason wildcard is forbidden outside the path.
- `--ses-prefix` sets the session prefix in the same manner as `sub-prefix` above
- `--no-subject` and `--no-session` are mandatory to indicate if the original dataset subjects and respectively
	sessions are not stored in dedicated folders. 
- `--recfolder folder=type` options indicates in what folders the actual data is stored, 
	and what is the type of data.
	For example `nii=MRI` tells that the `nii` subfolders contains MRI data. 
	The wildcard is allowed in the folder name.

`prepare` iteratively scans the original dataset and determine the subjects and sessions Id from 
folder names. Subject Id is taken from the name of top-most folder, and session from its sub-folder
(modulo the `prefix` parameters). 

The Id are taking as it, with removal of all non alphanumerical characters.
For example, if subject folder is called `s0123-control`, the subject Id will be 
`sub-s0123control`.
If the folders name contain a prefix, that you don't want to be part of Id, 
For example with option `--sub-prefix s`, the subject folder `s0123-control` will 
result in subject Id `sub-0123control`.

If in the original dataset data is not organized in `subject/session` folders,
one should use options `--no-subject` and `--no-session`.
The session Id will be set to an empty string, and subject Id will be retrieved
from data files.

> N.B. Even with subject and session folders present, there is a possibility to determine them directly from
data files. In order to do this  in corresponding [plugin](#wf_plugin) the `session.subject` must be set 
to `None`, making it undefined. But undefined subjects and sessions make subject selection unavailable.

If one need to rename subjects and/or sessions, it can be done with plug-in functions
`SubjectEP` and `SessionEP` or by renaming directly folders in the prepared dataset.

Once the data-files are identified, they are placed into prepared dataset, which follows 
loosely the basic BIDS structure:
```
sub-<subId>/ses-<sesId>/<DataType>/<Sequence>/data
```

The `sub-<subId>` and `ses-<sesId>` will be the bidsified version of subjects and sessions Id.
Note that if original dataset don't have sessions, the folder `sub-` will be present, with and empty 
`<sesId>`.

`<DataType>` folder will correspond to one of `bidsme` defined data types and will contain 
all data files identified as being of this type.

`<Sequence>` folders will group all data files corresponding to the same recording (for ex. 
different scanned volumes for the same MRI acquisition), it will be named as `<seqNo>-<secId>`
which will uniquely identify the sequence.

`prepare` do not modify/convert/rename data files, only copies them.
If an actual modification of data is needed (e.g. anonymisation, or conversion),
either in plugin functions `FileEP`, `SequenceEndEP` or manually in prepared
dataset. 
As long data files remains in the correct folders and data format is supported 
by BIDSme, bidsification should perform normally.

This structure has been chosen to be as rigid possible, in order to make it easier 
to treat numerically, but still human-readable.
It naturally  supports multimodal dataset.


A working example of source dataset and `prepare` configuration can be found 
[there](https://gitlab.uliege.be/CyclotronResearchCentre/Public/bidstools/bidsme/bidsme_example).

> NB: The logs for standard output and separately errors and warnings are stored
in destination folder in `code/bidsme/prepare/log` directory.

### <a name="wf_process"></a> Data processing

The processing is completely optional step between data preparation and
bidsification. It is intended to allow a data modification based on data identification
of `bidsme`. It can be used to check, pre-process data, convert it, merge etc.

It is not intended to run without plugins. It does nothing without, except checking
if all data is identifiable. It can be easily be replaced by a custom script. 

### <a name="wf_bids"></a>Data bidsification

Considering that the data is [prepeared](#wf_prep) together with 
[bidsmap](#wf_map) and [plugins](#wf_plug),
the bidsification is performed by `bidsify` command:
```
bidsme.py bidsify prepared bidsified
```

It will run over data-files in prepared dataset, determine the correct modalities
and BIDS entities, extract the meta-data needed for sidecar JSON files, and 
create BIDS dataset in destination folder.

Outside options cited [above](#gen_cli), `bidsify` accepts one parameter:

- `-b, --bidsmap` with path to the bidsmap file used to identify data files.
If omitted, the `bidsmap.yaml` will be used. Bidsmap will be searched first 
in local path, then in `bidsified/code/bidsme/`.

> N.B. It is advisable to first run bidsification in ["dry mode"](#gen_cli), using
switch `--dry-run`, then if there no errors detected run bidsification in normal mode.

The subjects and session Id are retrieved from folder structure, but still
can be modified in the plugins. It can be useful if one plan perform a random 
permutation on the subjects, for additional layer of anonymisation. 

> NB: The log files with messages and, separately the errors are stored in
destination directory in `source/bidsme/bidsify/log` sub-directory.


### <a name="wf_map"></a>Bidsmap configuration

Bidsmap is the central piece of BIDSme. 
It tells how to identify any data file, and what modality and bids labels 
to attribute.

It is a configuration file written in [YAML](http://yaml.org/) format, which is a 
compromise between human readability and machine parsing.

By default this file, once created is stored within bidsified dataset in 
`code/bidsme/bidsmap.yaml`.

The structure of a valid bidsmap is described in the section [Bidsmap file structure](#bidsmap).

The first step of creating a bidsmap is to prepare a reference dataset,
which is a subset of full dataset, containing only one or two subjects.
It is important to these subjects being complete (i.e. no missing scans)
and without errors made in protocol (no duplicated scans, scans in good order etc...).
This reference dataset will serve as a model for bidsmap.

Once the reference dataset is ready, the bidsmap is created by command `map`:
```
bidsme.py map prepeared/ bidsified/
```

The `map` command accepts two additional parameters:

- `-b, --bidsmap` (default: `bidsmap.yaml`), with path to the bidsmap file.
As in `bidsify` command given file will be searched first locally, then in 
`bidsified/code/bidsme/` directory. 
- `-t, --template` (default: `bidsmap-template.yaml`), with path to template map.
This file will be searched in order in local directory, default configuration directory 
(`$HOME/$XDG_CONFIG/bidsme/` on \*NIX, `\User\AppData\bidsme\` on Windows),
and in the `bidsme` installation directory.

At first pass tool will scan reference dataset and try to guess 
correct parameters for bidsification. If he can't find correct
parameters or could not identify the run, a corresponding warning
or error will be shown on stdout (and reported in the log file).
These warnings and errors should be corrected before re-run of
`bidsmapper`. 
The final goal is to achieve state than `bidsmapper` will no more produce
any warnings and errors.

> NB:If bidsifigation requires plugins, it is important to run `bidsmapper` 
with the same plugin.

Using [example 1](#ex1), the first pass of `bidsmapper` will produce around 500
warning, but they are repetitive. 

> WARNING MRI/001-localizer/0: No run found in bidsmap. Looking into template`

It means that give sample (first file - index `0`, of sequence `001-localizer`, 
of type `MRI`) wasn't identified in the bidsmap. `bidsmapper` will try to look 
in the template map to identify the sample. If sample is identified, then
`bidsmapper` will complete the bidsmap by information found in the template.
If sample is not identified in the template, a corresponding error will show
and samples attributes will be stored in `code/bidsmap/unknown.yaml`.
It is up to user to manually integrate this sample into bidsmap (and eventually
complete the template).

> `WARNING 002-cmrr_mbep2d_bold_mb2_invertpe/0: Placehoder found`

This warning tells that given sample is identified, but bids parameters
contains placeholder. To correct this warning it is enough to find
an corresponding entry in `bidsmap` and replaced placeholders by needed
values. 
The easiest way is to search for line `002-cmrr_mbep2d_bold_mb2_invertpe`:
```
- provenance: /home/beliy/Works/bidsme_example/example1/renamed/sub-001/ses-HCL/MRI/002-cmrr_mbep2d_bold_mb2_invertpe/f1513-0002-00001-000001-01.nii
        example: func/sub-001_ses-HCL_task-placeholder_acq-nBack_dir-PA_run-1_echo-1_bold
        template: true
        checked: false
        suffix: bold
        attributes:
          ProtocolName: cmrr_mbep2d_bold_mb2_invertpe
          ImageType: ORIGINAL\\PRIMARY\\M\\MB\\ND\\MOSAIC
        bids: !!omap
          - dir: PA
          - task: <<placeholder>>
....
```
and replace `task: <<placeholder>>` by `task: nBack`.

> NB: If the run is edited, it is a good practice to change `template: true`
to `template: false`. It will mark that this run is no more automatically
generated from template.

> `WARNING func/0: also checks run: func/1`
This warning indicates that first run of `func` modality and second one
checks the same scan. At first run it is normal, as samples are identified 
from template, and some overlaps are expected. If this warning remains in
subsequent passes, then the attributes of mentioned runs must be moved apart.

> `WARNING 012-t1_mpr_sag_p2_iso/0: Can't find 'ContrastBolusIngredient' attribute from '<ContrastBolusIngredient>'`
This warning means that `bidsmapper` can't extract given attribute from 
a scan. To correct the warning, cited attribute must be set manually, for ex.
in :
```
json: !!omap
          - ContrastBolusIngredient: <ContrastBolusIngredient>
```
change `<ContrastBolusIngredient>` to a used value (if contrast element is used),
or an empty string (otherwise).

> `WARNING 014-al_B1mapping/9: Naming schema not BIDS`
This warning appears when specified BIDS schema do not follows the standard. 
To correct this warning it will be enough to put bids section in bidsmap
into conform form ti the BIDS specifications. 
Alternately, if the deviation from the standard is intentional (e.g. 
given data type is not officially supported by BIDS), the warning can be silenced 
by setting `checked` to `true`. 

Bidsmap contain several automatically filled fields that are to simplify the map 
adjustments:

  - provenance: contains the path to the first data file matched to this run. 
This field is updated at each run of `bidsmapper`, but only if `checked` is 
false 
  - example: this field shows an generated bids name for the file in `provenance`
  - template: indicates if run was generated from template map. This value is 
not updated, and should be set to `false` at first manual edit
  - checked: indicates if operator checked the run and is satisfied with the
results. In order to bidsify dataset, all runs must be checked.

Finally `bidsify` command can be run of reference dataset, to assure that there 
no conflicts in definitions and the bidsified dataset is correct.



### <a name="wf_plug"></a>Plugin configuration
Plugins in BIDSme are implemented as a functions (entry point) that are called at 
specific time during the execution of main program. All of the commands `prepare`, 
`map`, `process` and `bidsify` are support the plugin.

All functions must be defined in the same python file, but it is possible include additional
files using the usual `import` instruction. The list of accepted functions is given in table below. 
Details on each of these functions can be found in [Plugins](#plugins) section

| Function | Entry point | Used for |
| ----------- | -------------- | ------------|
| `InitEP`  | At the start of program | Initialisation of plugin, setting global parameters |
| `SubjectEP` | After entering subject folder | Adjustment of subject Id |
| `SessionEP` | After entering session folder | Adjustment of session Id |
| `SequenceEP` | After loading first data file in sequence | Global sequence actions |
| `RecordingEP`| After loading a new data file in sequence | Adjustment of recording parameters |
| `FileEP`| After copying a data file to its dInitEP(source: str, destination: str,estination | Any post-copy adjustment |
| `SequenceEndEP`| After processing last file in the sequence | Any post-sequence treatments |
| `SessionEndEP`| After processing all sequences in session | Any post-session treatments |
| `SubjectEndEP`| After processing last subject | Any post-subject treatments |
| `FinaliseEP`| At the end of program | Any actions needed to finalise dataset |

Any of defined functions must accept a determined set of parameters, except `InitEP`, which
accept additional a set of optional named parameters, needed to setup any given plugin.

Each function is expected to return an ineger return code:

- **0** -- successful execution, program continues normally
- **None** -- interpreted as **0**
- **[0-9]** -- an error in plugin occurred, program will stop execution
 and `PluginError` will be raised
- **<0** -- an error in plugin occurred, current entity will be skipped

The negative code will affect only some of plugins, where skipping current entity
will have a meaning, namely `SubjectEP`, `SessionEP`, `SequenceEP` and `RecordingEP`.
For other function, negative code is interpreted as **0**

> NB: Even if all scripts supports the same list of entry points, some of them 
are more adapted for data preparation and other for bidsification.
From practice, it is more convenient to perform all subject and session
determination, data retrieval and additional files treatment during
preparation, and bidisification is concentrated on just renaming and 
copying files. This way, there an opportunity of checking, correcting 
and/or completing data manually. 

## <a name="examples"></a>Examples

### <a name="ex1"></a>Dataset 1

## <a name="formats"></a>Supported formats

BIDSme was designed for supporting different types of data (MRI, PET, EEG...)
and various data-files format. This is achieved using object-oriented approach.

Each data-type is viewed as sub-module of `Modules` and inherits from base class
`baseModule`, which defines the majority of logic needed for bidsification.

The sub-modules main classes (e.g. `Modules/MRI/MRI.py`) defines the bids-related 
information defines for this particular data-type, like the list of needed metadata for
JSON sidecar file or list of modalities and entities.

Finally for each data-type, several file-formats are treated by a separate class, that 
inherits from corresponding data-type class (e.g. `Modules/MRI/Nifti_SPM12.py`).
This class defines how extract needed meta-data from a particular file, how identify
a file, and similar file-related operations.	

### <a name="mri"></a>MRI
`MRI` data-type integrated all MRI images. The corresponding BIDS formatting can be
found [there](https://bids-specification.readthedocs.io/en/stable/04-modality-specific-files/01-magnetic-resonance-imaging-data.html).

It defines the following modalities:
- **anat** for [anatomical images](https://bids-specification.readthedocs.io/en/stable/04-modality-specific-files/01-magnetic-resonance-imaging-data.html#anatomy-imaging-data)
- **func** for [functional images](https://bids-specification.readthedocs.io/en/stable/04-modality-specific-files/01-magnetic-resonance-imaging-data.html#task-including-resting-state-imaging-data)
- **dwi** for [diffusion images](https://bids-specification.readthedocs.io/en/stable/04-modality-specific-files/01-magnetic-resonance-imaging-data.html#diffusion-imaging-data)
- **fmap** for [fieldmaps](https://bids-specification.readthedocs.io/en/stable/04-modality-specific-files/01-magnetic-resonance-imaging-data.html#fieldmap-data)

#### <a name="dicom"></a> DICOM
BIDSme support generic raw [DICOM](https://www.dicomstandard.org/) file format. 
Attributes extraction rely on [`pydicom`](https://pydicom.github.io/pydicom/stable/index.html) library.

DICOM files are identified by an extension `.dcm` and `.DCM`, and by word `DICM` placed in file at  `0x80`.

Attributes can be retrieved using both the DICOM tag and keyword (if defined).
For example `getField("InstanceCreationDate")` and `getField("(008, 0012)")` will both retrieve the same 
`Instance Creation Date`.
Tags must be **exatctly** in form of string formatted as follows: `"(%04d, %04d)"`, and the tag numbers
must be put in hexadecimal form without `0x` prefix -- the same way as DICOM tags are usually depicted.
Retrieved values are parsed if possible into python base values: `int`, `float`, `str`, `datetime.date`, 
`datetime.time` and `datetime.datetime`.

Nested values are retrieved using `/` separator, for example `getField("(2005, 140f)/0/PixelPresentation")` 
will retrieve Pixel Presentation value from private tag.
The navigation follows the same structure as pydicom: `ds[0x2005, 0x140f][0]["PixelPresentation"]`.
To retrieve values with multiplicity an index addressing each value must be used.
For example if `(0008, 0008) Image Type` is `['ORIGINAL', 'PRIMARY', 'M_FFE', 'M', 'FFE']`,
it can be accessed by `getField("ImageType/0") -> 'ORIGINAL'`. 

For convenience, during the preparation step, the full dump of DICOM header is created in form of JSON file
`dcm_dump_<dicom file name>.json`. 
In this dump, dataset structure is represented as dictionary, multi-values and sequences as lists.

#### <a name="hmriNIFTI"></a>hmriNIFTI
`hmriNIFTI` data-format is a DICOM files converted to Nifti format by 
[hMRI toolbox](https://www.sciencedirect.com/science/article/pii/S1053811919300291) for 
[SPM12](https://www.fil.ion.ucl.ac.uk/spm/software/spm12/). 
Essentially it consists by a nifti image data and a JSON file with DICOM header dumped into it.

All recording attributes are retrieved from `acqpar[0]` dictionary within json file,
requesting directly the name of corresponding field: `getField("SeriesNumber") -> 4`
In case of nested dictionaries, for ex. `"[CSAImageHeaderInfo"]["RealDwellTime"]`,
a field separator `/` should be used: 
```
getField("CSAImageHeaderInfo/RealDwellTime") -> 2700
```
In case of lists, individual elements are retrieved by passing the index:
```
getField("AcquisitionMatrix[3]") -> 72
```

The additional fields, that are not stored directly in JSON file, are calculated:
- **DwellTime** is retrieved from private field with tags `(0019,1018)` and converted from 
micro-seconds to seconds. 
- **NumberOfMeasurements** are retrieved from `lRepetitions` field and incremented by one.
- **PhaseEncodingDirection** are retrieved from `PhaseEncodingDirectionPositive`, and transformed 
to `1`(positive) or `-1`(negative)
- **B1mapNominalFAValues** are reconstructed from `adFree` and `alFree`. The exact reconstruction 
alghorytm is sequence dependent. 
- **B1mapMixingTime** are reconstructed from `adFree` and `alFree`. The exact reconstruction 
alghorytm is sequence dependent. 
- **RFSpoilingPhaseIncrement** are reconstructed from `adFree` and `alFree`. The exact reconstruction 
alghorytm is sequence dependent.
- **MTState** is retrieved from `[CSASeriesHeaderInfo"]["MrPhoenixProtocol"]["sPrepPulses"]` and set either 
to `On` of `Off`

> **Warning** These fields are guaranteed to be in the Siemens DICOM files, in case different origin, their
implementation must be either patched up or performed in plugins.

> **Warning** `B1mapNominalFAValues`, `B1mapMixingTime` and `RFSpoilingPhaseIncrement` are sequence
dependent. It is unclear to me if sequences names are standard or not. If outcome of these values produces
incorrect output, the correction must be either patched or corrected in plugin.

#### <a name="bidsmeNIFTI"></a>bidsmeNIFTI
`bidsmeNIFTI` dataformat is a generic NIFTI data file with a accompaigned DICOM header created
by BIDSme from original DICOM file, as described in [MRI/DICOM](#dicom) section.
It was introduced in order to use user-preferred DICOM converting tools without loosing any meta-data
from the initial file.

The JSON file conserves the same structure as original DICOM, with conservation of DICOM key words
if defined and tags (in form `"(%04d, %04d)"`) if not.

Te expected procedure to use this format is following:

	1. DICOM dataset is prepared as described [there](#wf_prep).
	2. DICOM files are converted to NIFTI format using tool of preference, but conserving the file
name (modulo the extention).
	3. DICOM files must be removed from prepared folder together with any JSON files created by 
converter to avoid data format mis-identifications and file double-counting.
	4 [process](#wf_process) and [bidsify](#wf_bidsify) steps will now use 
`dcm_dump_<dicom file name>.json`to identify recordings.

#### <a name=jsonNIFTI></a> jsonNIFTI
A lot of DICOM converters create a JSON file containing extracted meta-data. 
What metadata and how it is stored may vary unpredictably from one converter to another.

`jsonNIFTI` is an attempt to incorporate such converted files. 
The metadata is extracted from JSON file using same procedure as for [hmriNIFTI](#hmriNIFTI):
```
getField("CSAImageHeaderInfo/RealDwellTime") -> 2700
```

#### <a name=NIFTI> </a> NIFTI
A generic Nifti format implements [NIfti file format](os.path.join(directory, bidsname).
It's supports `ni1` (`.hdr + .img` files), `n+1` and `n+2` (`.nii`) formats.

Nifti files are identified by extension, either `.hdr` or `.nii`, and 
the first 4 bytes of file: it must encode either `348` or `540`. 
As Nifti do not impose the endianess of file, both little and big 
endiannes is checked.

Base attributes are extracted directly from header, and conserve 
the name as defined
[here](https://brainder.org/2012/09/23/the-nifti-file-format/)
and [here](https://brainder.org/2015/04/03/the-nifti-2-file-format/),
or alternatively in `C` header file for 
[`ni1/n+1`](https://nifti.nimh.nih.gov/pub/dist/src/niftilib/nifti1.h)
and [`n+2`](https://nifti.nimh.nih.gov/pub/dist/doc/nifti2.h).
For example, the image x-dimension can be accessed by
`getAttribute("dim/1")`.

The Nifti header do not contain information used to identify given
recording, like protocol name, subject Id, Sequence etc.
To identify recordings these values must be set in plugins using
`setAttribute(name, value)` function.
If they are not set manually, a default value will be used.
If filename is formatted in bids-like way, the default subject Id 
and session Id are extracted from file name, if not a null value `None`
will be used.

|Attribute name| Default value|
|--------------------|------------------|
|`PatientId`			| `sub-<subId>` or `None` |
|`SessionId`			| `ses-<sesId>` or `None` |
|`RecordingId`		| filename without extension |
|`RecordingNumber`	| index of current file |
|`AcquisitionTime`		| `None`|


### <a name="eeg"></a>EEG
`EEG` data-type integrated all EEG recordings. 
The corresponding BIDS formatting can be
found [there](https://bids-specification.readthedocs.io/en/stable/04-modality-specific-files/03-electroencephalography.html).

It defines the modality **eeg**.
Outside the data files, BIDS requires also export of channels and events
(if present) data in `.tsv` files accompagnied by sidecar JSON file.

#### <a name="BV"></a>BrainVision

## <a name="plugins"></a>Plug-in functions

#### <a name="plug_init"></a> `InitEP(source: str, destination: str, dry: bool, **kwargs) -> int:`
The `InitEP` function is called immediately after start of main program. 
As name indicates, it initialise the plugin, store the global variables and parameters.

It accepts 3 mandatory parameters:
 - **source: str**: a path to the source directory, from where data files are processed.
 - **destination: str**: a path to destination directory, where processed data will be stored
 - **dry: bool**: a switch to indicate if it is a dry-run (i.e. a test run where nothing is written to disk)

> **Warning**: `dry` parameter must be always stored as global parameter, 
and **any** file and folder modification parts in the plugins **must** be protected 
by check if `dry` is `False`:
```python
if not dry:
	do stuff
	....
```
 
 The custom additional parameters can be received via `**kwargs`. These parameters are communicated 
 to the program via `-o` option:
 ```
 -o par1=val1 -o par2=val2
 ```
 These parameters will be parsed into dictionary and feeded to `InitEP`:
 ```
 {
 	"par1": "val1",
 	"par2": "val2"
 }
 ```, 
 or from within a `bidsmap.yaml` file, in the  `Option/PlugIns/options` section, directly as a dictionary. 

The `source`, `destination` and `dry` values must be stored as global parameters, so they can
be used in other plugins:

```python
global source_path
source_path = source
```

Outside the definition and storage of global parameters, `InitEP` can be used for loading
and parsing external files. For example, in [Example1](#ex1), the `Appariement.xlsx`
excel file, containing the list of subjects is parced. 
The parsed excel file is used later to identify sessions and fill the `participant.tsv` file.

If `--part-template` option is not used in `coinsort`, then the template
 json file for `participants.tsv` can be done there, using 
 `BidsSession.loadSubjectFields(cls, filename: str=None)` class
 function. 
 
> In order to maintain consistency between subjects, template json
file can be loaded only once. Subsequent loading will raise an exception.

#### <a name="plug_sub"></a> `SubjectEP(scan: BidsSession) -> int`
The `SubjectEP` function is called after entering the subject's folder. 
The main action of this function is redefinition of subject Id and filling
meta-data associated with given subject.
The passed parameter `scan` ia s `BidsSession` mutable object,
with proprieties:
- **subject**: containing current subject Id
- **session**: containing current session Id
- **in_path**: containing current path
- **sub_values**: containing a dictionary of current subject
data destined for `participants.tsv`

In order to change subject, it will suffice to change the `subject`
property of BidsSession:
```python
scan.subject = scan.subject + "patient"
```

It is not necessary to add `ses-` to the subject name, it will be added
automatically, together with removal of all non alphanumerical characters.
So subject Id is guaranteed to be bids-compatible.

`sub_values` is a dictionary with `participants.tsv` columns as keys and `None` as values.
Filling values will populate the corresponding line in `participants.tsv`.

> The columns are normally defined by template JSON file during 
preparation step, but they can be loaded from within plugin
during `InitEP` execution.

#### <a name="plug_ses"></a> `SessionEP(scan: BidsSession) -> int`
`SessionEP` is executed imideatly after entering session folder, and 
mean to modify current session Id.
It accepts the same `BidsSession` object as `SubjectId`, with not yet bidsified
names.

> Immediatly after execution of `SessionEP`, the `subject` and `session` 
properties of `scan` are bidsified and locked. No changes will be accepted,
any attempt will raise an exception. Howether it can be unlocked at your 
risk and peril by calling `scan.unlock_subject()` and 
`scan.unlock_session()`. It can broke the preparation/bidsification!

#### <a name="plug_seq"></a> `SequenceEP(recording: object) -> int`
`SequenceEP` is executed at the start of each sequence.
It can be used to perform global sequence check and actions checking validity.

Passed parameter is an actual recording with loaded first file (in alphabetical 
order).
The current subject and session can be accessed via `recording.subId()`
and `recording.sesId()`, but other BIDS attributes are not yet defined.

In the [Example1](#ex1), during bidsification step, this plugin is used
to determine the destination of fieldmaps:
```python
if recid == "gre_field_mapping":
	if recording.sesId() in ("ses-HCL", "ses-LCL"):
		Intended = "HCL/LCL"
	elif recording.sesId() == "ses-STROOP":
		Intended = "STROOP"
```
The global intended variable used later in plugin to correctly fill
`IntendedFor` json file.

#### <a name="plug_rec"></a> `RecordingEP(recording: object) -> int`
`RecordingEP` is executed immidiatly after loading a new file in each of 
recordings. It is used for locally adapting the attributes of recording.

For example, in [Example 1](#ex_1), sorting plugin executes:
```python
if Intended != "":
	recording.setAttribute("SeriesDescription", Intended)
```
, replacing the `SeriesDescription` by global variable `Intended`, defines
during `SequenceEP`.

> The changed attribute can be restored to it original value by executing
`recording.unsetAttribute("SeriesDescription")`

#### <a name="plug_recEnd"></a> `FileEP(path: str, recording: object) -> int`
`FileEP` is called after the copy of recording file to its destination
(either during preparation or bidsification).

Outside the `recording` object, it accepts the `path` parameter containing
the path to copied file.

The utility of this plugin is data file manipulation, for example 
the convertion into another format, or anonymisation. 
Working only on the copy of original file do not compromise the source dataset.

#### <a name="plug_seqEnd"></a> `SequenceEndEP(path: str, recording: object) -> int`
The `SequenceEndEP` is called after the treatment of all files in the sequence, 
and can be used to perform various checks and/or sequence files manipulation,
for example compressing files or packing 3D MRI images into 4D one.

Sa in `FileEP` function, `path` parameter contains the path to the directory
where last file of given sequence is copied. The `recording` object also
have last file in sequence loaded.

#### <a name="plug_sesEnd"></a> `SessionEndEP(scan: BidsSession) -> int`
`SessionEndEP` is executed after treating the last sequence of recording.
As there no loaded recordings, it takes `BidsSession` as parameter. 
The mean goal of this function is check of compliteness of session,
and retrieving metadata of session, for example parcing various 
behevirial data.

#### <a name="plug_subEnd"></a> `SubjectEndEP(scan: BidsSession) -> int`
`SubjectEndEP` is executed after treating the last session of a given
subject. 
It can be used for checking if all sessions are present, and for 
retrieval of phenotype data for given subject.

#### <a name="plug_End"></a> `FinaliseEP() -> int`
`FinaliseEP` is called in the end of programm and can be used
for consolidation and final checks of destination dataset.

## <a name="new_formats"></a>Implementing additional formats

## <a name="bidsmap"></a>Bidsmap file structure
