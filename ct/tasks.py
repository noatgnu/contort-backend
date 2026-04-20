import copy
import os
import select
import subprocess
import sys

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django_rq import job
from ct.models import ConsurfJob
from django.conf import settings


@job('default', timeout=24*60*60)
def run_consurf_job(job_id: int, session_id: str):
    channel = get_channel_layer()
    consurf_job = ConsurfJob.objects.get(id=job_id)
    async_to_sync(channel.group_send)(
        f'job_{session_id}',
        {
            'type': 'job_message',
            'message': {
                'job_id': job_id,
                'status': consurf_job.status,
                'session_id': session_id,
                'log_data': "",
                'error_data': "",
                'message': "Job started"
            }

        }
    )
    env = copy.deepcopy(os.environ)
    env['PYTHONPATH'] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env['VIRTUAL_ENV'] = os.getenv('VIRTUAL_ENV', '')
    env['PATH'] = os.path.dirname(sys.executable) + os.pathsep + env['PATH']
    pipe_out = []
    pipe_err = []
    media_path = settings.MEDIA_ROOT
    job_path = os.path.join(media_path, "consurf_jobs", str(job_id))
    os.makedirs(job_path, exist_ok=True)
    consurf_job.status = 'running'
    command = [
        sys.executable,
        '-u',
        'stand_alone_consurf.py',
        '--dir', job_path,
        '--model', consurf_job.substitution_model,
    ]
    if consurf_job.query_sequence:
        query_file = os.path.join(job_path, "query.fasta")
        with open(query_file, 'w') as f:
            f.write(consurf_job.query_sequence)
        command.extend(['--seq', query_file])
    if consurf_job.fasta_database:
        command.extend([
            '--DB', consurf_job.fasta_database.fasta_file.path,
            '--MAX_HOMOLOGS', str(consurf_job.max_homologs),
            '--iterations', str(consurf_job.max_iterations),
            '--MAX_ID', str(consurf_job.max_id),
            '--MIN_ID', str(consurf_job.min_id),
            '--cutoff', str(consurf_job.cutoff),
            '--algorithm', consurf_job.algorithm,
        ])
    if consurf_job.maximum_likelihood:
        command.append("--Maximum_Likelihood")
    if consurf_job.closest:
        command.append("--closest")
    if consurf_job.msa:
        command.extend(['--msa', consurf_job.msa.msa_file.path])
        if consurf_job.alignment_program:
            command.extend(['--align', consurf_job.alignment_program])
    elif consurf_job.fasta_database and consurf_job.alignment_program:
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

    line_count = 0
    save_interval = 10
    watched = [process.stdout, process.stderr]

    while watched or process.poll() is None:
        readable, _, _ = select.select(watched, [], [], 0.1)

        if not readable:
            continue

        has_new_output = False

        for fd in list(readable):
            data = fd.readline()
            if not data:
                watched.remove(fd)
                continue
            if fd is process.stdout:
                pipe_out.append(data.decode())
            else:
                pipe_err.append(data.decode())
            has_new_output = True
            line_count += 1

        if has_new_output:
            consurf_job.log_data = "".join(pipe_out)
            consurf_job.error_data = "".join(pipe_err)
            line_count += 1
            if line_count >= save_interval:
                consurf_job.save()
                line_count = 0

            async_to_sync(channel.group_send)(
                f'job_{session_id}',
                {
                    'type': 'job_message',
                    'message': {
                        'job_id': job_id,
                        'status': consurf_job.status,
                        'session_id': session_id,
                        'log_data': consurf_job.log_data,
                        'error_data': consurf_job.error_data,
                        'message': ""
                    }
                }
            )

    consurf_job.log_data = "".join(pipe_out)
    consurf_job.error_data = "".join(pipe_err)
    consurf_job.status = 'completed' if process.returncode == 0 else 'failed'
    if os.path.exists(os.path.join(job_path, "Consurf_Outputs.zip")):
        consurf_job.status = 'completed'
    else:
        consurf_job.status = 'failed'
    async_to_sync(channel.group_send)(
        f'job_{session_id}',
        {
            'type': 'job_message',
            'message': {
                'job_id': job_id,
                'status': consurf_job.status,
                'session_id': session_id,
                'log_data': "",
                'error_data': "",
                'message': ""
            }
        }
    )

    consurf_job.save()
    return consurf_job.id