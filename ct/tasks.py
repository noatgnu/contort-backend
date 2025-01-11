import copy
import os
import subprocess
import sys

from django_rq import job
from ct.models import ConsurfJob
from django.conf import settings


@job('default', timeout='3h')
def run_consurf_job(job_id: int):
    consurf_job = ConsurfJob.objects.get(id=job_id)
    env = copy.deepcopy(os.environ)
    env['PYTHONPATH'] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env['VIRTUAL_ENV'] = os.getenv('VIRTUAL_ENV', '')
    env['PATH'] = os.path.dirname(sys.executable) + os.pathsep + env['PATH']
    pipe_out = []
    pipe_err = []
    media_path = settings.MEDIA_ROOT
    job_path = os.path.join(media_path, "consurf_jobs", str(job_id))
    os.makedirs(job_path, exist_ok=True)
    query_file = os.path.join(job_path, "query.fasta")
    with open(query_file, 'w') as f:
        f.write(f"{consurf_job.query_sequence}")
    consurf_job.status = 'running'
    command = [
            sys.executable,
            'stand_alone_consurf.py',
            '--seq', query_file,
            '--dir', job_path,
            '--DB', consurf_job.fasta_database.fasta_file.path,
            '--align', consurf_job.alignment_program,
            '--MAX_HOMOLOGS', str(consurf_job.max_homologs),
            '--iterations', str(consurf_job.max_iterations),
            '--model', consurf_job.substitution_model,
            '--MAX_ID', str(consurf_job.max_id),
            '--MIN_ID', str(consurf_job.min_id),
            '--cutoff', str(consurf_job.cutoff),
            '--iterations', str(consurf_job.max_iterations),
            '--algorithm', consurf_job.algorithm,
        ]
    if consurf_job.maximum_likelihood:
        command.append("--Maximum_Likelihood")
    if consurf_job.closest:
        command.append("--closest")
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        cwd="/workspace/stand_alone_consurf/"
    )
    consurf_job.process_cmd = " ".join(process.args)
    consurf_job.save()
    while process.poll() is None:
        line = process.stdout.readline()
        if line:
            pipe_out.append(line.decode())
            consurf_job.log_data = "".join(pipe_out)
        line = process.stderr.readline()
        if line:
            pipe_err.append(line.decode())
            consurf_job.error_data = "".join(pipe_err)
        consurf_job.save()

    consurf_job.status = 'completed' if process.returncode == 0 else 'failed'
    consurf_job.save()
    return consurf_job.id