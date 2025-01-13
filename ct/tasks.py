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
    if consurf_job.msa:
        command.extend(['--msa', consurf_job.msa.msa_file.path])
    else:
        if consurf_job.alignment_program:
            command.extend(['--align', consurf_job.alignment_program])
    if consurf_job.structure_file and consurf_job.chain:
        command.extend(['--structure', consurf_job.structure_file.structure_file.path, '--chain', consurf_job.chain])
    if consurf_job.query_name:
        command.extend(['--query', consurf_job.query_name])
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        cwd="/workspace/stand_alone_consurf/"
    )
    consurf_job.process_cmd = " ".join(process.args)
    consurf_job.save()
    while True:
        output = process.stdout.readline()
        error = process.stderr.readline()
        if output == b'' and error == b'' and process.poll() is not None:
            break
        if output:
            pipe_out.append(output.decode())
            consurf_job.log_data = "".join(pipe_out)
        if error:
            pipe_err.append(error.decode())
            consurf_job.error_data = "".join(pipe_err)
        consurf_job.save()
    consurf_job.status = 'completed' if process.returncode == 0 else 'failed'
    if os.path.exists(os.path.join(job_path, "Consurf_Outputs.zip")):
        consurf_job.status = 'completed'
    else:
        consurf_job.status = 'failed'

    consurf_job.save()
    return consurf_job.id