import os
import multiprocessing as mp
from copy import copy
from tempfile import NamedTemporaryFile, gettempdir
from subprocess import Popen
from pathlib import Path


def get_num_threads(threads):
    """It returns num of threads to use in parallel.

    You can pass to the funaction the  memory you want to use each thread.
    It calculates the number of treads
    In megabytes
    """
    phisical_threads = os.sysconf('SC_NPROCESSORS_ONLN')
    if not threads:
        return 1
    elif isinstance(threads, bool):
        return phisical_threads
    else:
        return threads


def map_process_to_sortedbam(map_process, out_fpath, key='coordinate',
                             stderr_fhand=None, tempdir=None):
    if stderr_fhand is None:
        stderr = NamedTemporaryFile(suffix='.stderr')
    else:
        stderr = stderr_fhand

    if tempdir is None:
        tempdir = gettempdir()

    cmd = ['samtools', 'sort', '-o', out_fpath]
    sort = Popen(cmd, stdin=map_process.stdout, stderr=stderr)
    map_process.stdout.close()
    sort.communicate()
    if map_process.returncode:
        raise RuntimeError('Error in mapping process')

    if sort.returncode:
        raise RuntimeError('Error in Sort process')


def run_multiprocesses(func, confs, num_processes, log_fhand):
    pool = mp.Pool(processes=num_processes)
    results = pool.imap_unordered(func, confs)
    for result in results:
        failed = result['fail']
        sample = result['sample']
        msg = result['error_msg']
        if failed:
            log_fhand.write('ERROR: {}, {}\n'.format(sample, msg))
        else:
            log_fhand.write('OK: {}\n'.format(sample))
        log_fhand.flush()


def generate_bwa_confs_from_project(samples_fpath, bwa_index, do_duplicates,
                                    do_downgrade_edges, tmp_dir, read_dir,
                                    out_dir, threads=1):
    confs = []
    tmp_dirpath = Path(tmp_dir)
    skeleton = {'threads': threads, 'do_downgrade_edges': do_downgrade_edges,
                'do_duplicates': do_duplicates, 'index': bwa_index,
                'tmpdir': str(tmp_dirpath.absolute())}
    out_dirpath = Path(out_dir)
    read_dirpath = Path(read_dir)

    sample_path = Path(samples_fpath)

    for line in open(str(sample_path)):
        conf = copy(skeleton)
        line = line.strip()
        items = line.split()
        library = items[0]
        try:
            sample = items[1]
        except IndexError:
            sample = library
        read1_path = read_dirpath.joinpath('{}_1.fastq.gz'.format(library))
        read2_path = read_dirpath.joinpath('{}_2.fastq.gz'.format(library))
        out_path = out_dirpath.joinpath('{}.bam'.format(library))
        conf['read1_fpath'] = str(read1_path.absolute())
        conf['read2_fpath'] = str(read2_path.absolute())
        conf['out_fpath'] = str(out_path.absolute())
        conf['sample'] = sample
        conf['library'] = library
        confs.append(conf)

    return confs


def remove_fhand(fhand):
    fpath = fhand.name
    fhand.close()
    if os.path.exists(fpath):
        os.remove(fpath)
