#!/usr/bin/env python
"""
Process bidsified dataset before the bidsification.
Can be used to produce derivatives, convertion
anonymisation with adventage of recording identification
by bidsmap.yaml

Essentually it is identical to bidsification but without
bidsification itself.
"""

import os
import logging
import pandas

from tools import tools
import plugins

import Modules
from bidsmap import Bidsmap
from bids import BidsSession

logger = logging.getLogger(__name__)


def coin(destination: str,
         recording: Modules.baseModule,
         bidsmap: Bidsmap,
         dry_run: bool) -> None:
    """
    Converts the session dicom-files into BIDS-valid nifti-files
    in the corresponding bidsfolder and extracts personals
    (e.g. Age, Sex) from the dicom header

    :param session:     The full-path name of the subject/session source folder
    :param bidsmap:     The full mapping heuristics from the bidsmap YAML-file
    :param personals:   The dictionary with the personal information
    :param subprefix:   The prefix common for all source subject-folders
    :param sesprefix:   The prefix common for all source session-folders
    :return:            Nothing
    """
    if plugins.RunPlugin("SequenceEP", recording) < 0:
        logger.warning("Sequence {} discarded by {}"
                       .format(recording.recIdentity(False),
                               "SequenceEP"))
        return

    logger.info("Processing: sub '{}', ses '{}', {} ({} files)"
                .format(recording.subId(),
                        recording.sesId(),
                        recording.recIdentity(),
                        len(recording.files)))

    recording.sub_BIDSvalues["participant_id"] = recording.subId()

    recording.index = -1
    while recording.loadNextFile():
        if plugins.RunPlugin("RecordingEP", recording) < 0:
            logger.warning("Recording {} discarded by {}"
                           .format(recording.recIdentity(),
                                   "RecordingEP"))
            continue

        recording.getBidsSession().registerFields(True)
        out_path = os.path.join(destination,
                                recording.getBidsPrefix("/"))
        # checking in the current map
        modality, r_index, r_obj = bidsmap.match_run(recording)
        if not modality:
            e = "{}: No compatible run found"\
                .format(recording.recIdentity())
            logger.error(e)
            raise ValueError(e)
        if modality == Modules.ignoremodality:
            logger.info('{}: ignored modality'
                        .format(recording.recIdentity()))
            continue
        recording.setLabels(r_obj)
        recording.generateMeta()

        bidsname = recording.getBidsname()
        bidsmodality = os.path.join(out_path, recording.Modality())

        # Check if file already exists
        if os.path.isfile(os.path.join(bidsmodality,
                                       bidsname + '.json')):
            e = "{}/{}.json exists at destination"\
                .format(bidsmodality, bidsname)
            logger.error(e)
        if not dry_run:
            plugins.RunPlugin("FileEP",
                              recording.getBidsSession().in_path,
                              recording)
        else:
            plugins.RunPlugin("FileEP",
                              None,
                              recording)
    if not dry_run:
        plugins.RunPlugin("SequenceEndEP",
                          recording.getBidsSession().in_path,
                          recording)
    else:
        plugins.RunPlugin("SequenceEndEP", None, recording)


def process(source: str, destination: str,
            plugin_file: str = "",
            plugin_opt: dict = {},
            sub_list: list = [],
            sub_skip_tsv: bool = False,
            sub_skip_dir: bool = False,
            ses_skip_dir: bool = False,
            part_template: str = "",
            bidsmapfile: str = "bidsmap.yaml",
            dry_run: bool = False
            ) -> None:
    """
    Process bidsified dataset before the bidsification.
    Can be used to produce derivatives, convertion
    anonymisation with adventage of recording identification
    by bidsmap.yaml

    Essentually it is identical to bidsification but without
    bidsification itself.

    Only subjects in source/participants.tsv are treated,
    this list can be narrowed using sub_list, sub_skip_tsv
    and sub_skip_dir options

    Parameters
    ----------
    source: str
        folder containing source dataset
    destination: str
        folder for prepeared dataset
    plugin_file: str
        path to the plugin file to use
    plugin_opt: dict
        named options passed to plugin
    sub_list: list
        list of subject to process. Subjects
        are checked after plugin and must
        start with 'sub-', as in destination
        folder
    sub_skip_tsv: bool
        if set to True, subjects found in
        destination/participants.tsv will be
        ignored
    sub_skip_dir: bool
        if set to true, subjects with already
        created directories will be ignored
        Can conflict with sub_no_dir
    ses_skip_dir: bool
        if set to True, sessions with already
        created directories will be ignored
        Can conflict with ses_no_dir
    part_template: str
        path to template json file, from whitch
        participants.tsv will be modeled. If unset
        the defeault one "source/participants.tsv"
        is used. Setting this variable may break
        workflow
    bidsmapfile: str
        The name of bidsmap file, will be searched for
        in destination/code/bidsmap directory, unless
        path is absolute
    dry_run: bool
        if set to True, no disk writing operations
        will be performed
    """

    logger.info("-------------- Processing data -------------")
    logger.info("Source directory: {}".format(source))
    logger.info("Destination directory: {}".format(destination))

    # Input checking
    # source = os.path.abspath(source)
    if not os.path.isdir(source):
        logger.critical("Source directory {} don't exists"
                        .format(source))
        raise NotADirectoryError(source)
    if not os.path.isdir(destination):
        logger.critical("Destination directory {} don't exists"
                        .format(destination))
        raise NotADirectoryError(destination)

    # Input checking & defaults
    bidscodefolder = os.path.join(destination, 'code', 'bidscoin')

    # Create a code/bidscoin subfolder
    os.makedirs(bidscodefolder, exist_ok=True)

    # Check for dataset description file
    dataset_file = os.path.join(destination, 'dataset_description.json')
    if not os.path.isfile(dataset_file):
        logger.warning("Dataset description file 'dataset_description.json' "
                       "not found in '{}'".format(destination))

    # Check for README file
    readme_file = os.path.join(destination, 'README')
    if not os.path.isfile(readme_file):
        logger.warning("Dataset readme file 'README' "
                       "not found in '{}'".format(destination))

    # Get the bidsmap heuristics from the bidsmap YAML-file
    bidsmapfile = os.path.join(bidscodefolder, bidsmapfile)
    logger.info("loading bidsmap {}".format(bidsmapfile))
    bidsmap = Bidsmap(bidsmapfile)

    if not bidsmap:
        logger.critical('Bidsmap file {} not found.'
                        .format(bidsmapfile))
        raise FileNotFoundError(bidsmapfile)

    ntotal, ntemplate, nunchecked = bidsmap.countRuns()
    logger.debug("Map contains {} runs".format(ntotal))
    if ntemplate != 0:
        logger.warning("Map contains {} template runs"
                       .format(ntemplate))
    if nunchecked != 0:
        logger.critical("Map contains {} unchecked runs"
                        .format(nunchecked))
        raise Exception("Unchecked runs present")

    ###############
    # Plugin setup
    ###############
    if plugin_file:
        plugins.ImportPlugins(plugin_file)
        plugins.InitPlugin(source=source,
                           destination=destination,
                           dry=dry_run,
                           **plugin_opt)

    ###############################
    # Checking participants list
    ###############################
    if not part_template:
        part_template = os.path.join(source, "participants.json")
    else:
        logger.warning("Loading exterior participant template {}"
                       .format(part_template))
    BidsSession.loadSubjectFields(part_template)

    new_sub_file = os.path.join(source, "participants.tsv")
    df_sub = pandas.read_csv(new_sub_file,
                             sep="\t", header=0,
                             na_values="n/a").drop_duplicates()
    df_dupl = df_sub.duplicated("participant_id")
    if df_dupl.any():
        logger.critical("Participant list contains one or several duplicated "
                        "entries: {}"
                        .format(", ".join(df_sub[df_dupl]["participant_id"]))
                        )
        raise Exception("Duplicated subjects")

    dupl_file = os.path.join(source, "__duplicated.tsv")
    if os.path.isfile(dupl_file):
        logger.critical("Found unmerged file with duplicated subjects")
        raise FileExistsError(dupl_file)

    new_sub_json = os.path.join(source, "participants.json")
    if not tools.checkTsvDefinitions(df_sub, new_sub_json):
        raise Exception("Incompatible sidecar json")

    old_sub_file = os.path.join(destination, "participants.tsv")
    old_sub = None
    if os.path.isfile(old_sub_file):
        old_sub = pandas.read_csv(old_sub_file, sep="\t", header=0,
                                  na_values="n/a")
        if not old_sub.columns.equals(df_sub.columns):
            logger.warning("Source participant.tsv has different columns "
                           "from destination dataset")
        old_sub = old_sub["participant_id"]

    ##############################
    # Subjects loop
    ##############################
    n_subjects = len(df_sub["participant_id"])
    for index, sub_row in df_sub.iterrows():
        sub_no = index + 1
        sub_id = sub_row["participant_id"]
        sub_dir = os.path.join(source, sub_id)
        if not os.path.isdir(sub_dir):
            logger.error("{}: Not found in {}"
                         .format(sub_id, source))
            continue

        scan = BidsSession()
        scan.in_path = sub_dir
        scan.subject = sub_id

        #################################################
        # Cloning df_sub row values in scans sub_values
        #################################################
        for column in df_sub.columns:
            scan.sub_values[column] = sub_row[column]

        # locking subjects here forbids renaming in process
        # as it will be unclear how manage folders with data
        scan.lock_subject()
        if plugins.RunPlugin("SubjectEP", scan) < 0:
            logger.warning("Subject {} discarded by {}"
                           .format(scan.subject, "SubjectEP"))
            continue

        if not scan.isSubValid():
            logger.error("{}: Subject id '{}' is not valid"
                         .format(sub_id, scan.subject))
            continue

        if tools.skipEntity(scan.subject, sub_list,
                            old_sub if sub_skip_tsv else None,
                            destination if sub_skip_dir else ""):
            logger.info("Skipping subject '{}'"
                        .format(scan.subject))
            continue

        ses_dirs = tools.lsdirs(sub_dir, 'ses-*')
        if not ses_dirs:
            logger.error("{}: No sessions found in: {}"
                         .format(scan.subject, sub_dir))
            continue

        for ses_dir in ses_dirs:
            scan.in_path = ses_dir
            logger.info("{} ({}/{}): Scanning folder {}"
                        .format(scan.subject,
                                sub_no,
                                n_subjects,
                                ses_dir))
            scan.unlock_session()
            scan.session = os.path.basename(ses_dir)
            if plugins.RunPlugin("SessionEP", scan) < 0:
                logger.warning("Session {} discarded by {}"
                               .format(scan.session, "SessionEP"))
                continue

            scan.lock()

            if ses_skip_dir and tools.skipEntity(scan.session,
                                                 [], None,
                                                 os.path.join(destination,
                                                              scan.subject)):
                logger.info("Skipping session '{}'"
                            .format(scan.session))
                continue

            for module in Modules.selector.types_list:
                mod_dir = os.path.join(ses_dir, module)
                if not os.path.isdir(mod_dir):
                    logger.debug("Module {} not found in {}"
                                 .format(module, ses_dir))
                    continue
                for run in tools.lsdirs(mod_dir):
                    scan.in_path = run
                    cls = Modules.select(run, module)
                    if cls is None:
                        logger.error("Failed to identify data in {}"
                                     .format(run))
                        continue
                    recording = cls(rec_path=run)
                    if not recording or len(recording.files) == 0:
                        logger.error("unable to load data in folder {}"
                                     .format(run))
                        continue
                    recording.setBidsSession(scan)
                    coin(destination, recording, bidsmap, dry_run)

    ##################################
    # Merging the participants table
    ##################################
    df_processed = BidsSession.exportAsDataFrame()

    col_mismatch = False
    if not df_processed.columns.equals(df_sub.columns):
        col_mismatch = True
        logger.warning("Modified participant table do not match "
                       "original table. This is discouraged and can "
                       "break future preparation and process steps")
        for col in df_processed.columns.difference(df_sub.columns):
            df_sub[col] = None
        df_sub = df_sub[BidsSession.getSubjectColumns()]
        df_sub.drop_duplicates(inplace=True)

    df_res = pandas.concat([df_sub, df_processed], join="inner",
                           keys=("original", "processed"),
                           names=("stage", "ID"))
    df_res = df_res.drop_duplicates()

    df_dupl = df_res.duplicated("participant_id", keep=False)

    if df_dupl.any():
        logger.info("Updating participants values")
        df_dupl = df_dupl.drop(["processed"])
        df_res.drop(df_dupl[df_dupl].index, inplace=True)

    df_dupl = df_res.duplicated("participant_id")
    if df_dupl.any():
        logger.error("Participant list contains one or several duplicated "
                     "entries: {}"
                     .format(", ".join(df_res[df_dupl]["participant_id"]))
                     )

    ##################################
    # Saving the participants table
    ##################################
    if not dry_run:
        df_res[~df_dupl].to_csv(new_sub_file,
                                sep='\t', na_rep="n/a",
                                index=False, header=True)
        if df_dupl.any():
            logger.info("Saving the list to be merged manually to {}"
                        .format(dupl_file))
            df_res[df_dupl].to_csv(dupl_file,
                                   sep='\t', na_rep="n/a",
                                   index=False, header=True)
        json_file = tools.change_ext(new_sub_file, "json")
        if col_mismatch or not os.path.isfile(json_file):
            BidsSession.exportDefinitions(json_file)

    plugins.RunPlugin("FinaliseEP")