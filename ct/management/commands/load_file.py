import os
from pathlib import Path

from django.core.files import File
from django.core.management import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction

from ct.models import ProteinFastaDatabase, StructureFile, MultipleSequenceAlignment


class Command(BaseCommand):
    """
    Load FASTA database, PDB structure, or MSA file for a specific user.

    Usage:
        python manage.py load_file <file_type> <file_path> --user <username> --name <file_name>

    file_type: fasta, pdb, or msa
    """

    def add_arguments(self, parser):
        parser.add_argument('file_type', type=str, choices=['fasta', 'pdb', 'msa'],
                          help='Type of file: fasta, pdb, or msa')
        parser.add_argument('file_path', type=str, help='Path to the file')
        parser.add_argument('--user', type=str, required=True, help='Username to associate the file with')
        parser.add_argument('--name', type=str, required=False, help='Name for the file (default: filename)')
        parser.add_argument('--chains', type=str, required=False, help='Chains for PDB file (comma-separated)')
        parser.add_argument('--public', action='store_true', help='Make file public')
        parser.add_argument('--share-with', type=str, required=False, help='Comma-separated list of usernames to share with')

    def handle(self, *args, **options):
        file_type = options['file_type']
        file_path = options['file_path']
        username = options['user']
        file_name = options.get('name')
        chains = options.get('chains')
        is_public = options.get('public', False)
        share_with = options.get('share_with')

        if not os.path.isfile(file_path):
            self.stdout.write(self.style.ERROR(f'File not found: {file_path}'))
            return

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User not found: {username}'))
            return

        share_with_users = []
        if share_with:
            usernames = [u.strip() for u in share_with.split(',')]
            share_with_users = User.objects.filter(username__in=usernames)
            missing_users = set(usernames) - set(u.username for u in share_with_users)
            if missing_users:
                self.stdout.write(self.style.WARNING(f'Users not found: {", ".join(missing_users)}'))

        if not file_name:
            file_name = Path(file_path).stem

        with transaction.atomic():
            try:
                if file_type == 'fasta':
                    self._load_fasta(file_path, file_name, user, is_public, share_with_users)
                elif file_type == 'pdb':
                    self._load_pdb(file_path, file_name, user, chains, is_public, share_with_users)
                elif file_type == 'msa':
                    self._load_msa(file_path, file_name, user, is_public, share_with_users)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error loading file: {str(e)}'))
                raise

    def _load_fasta(self, file_path, file_name, user, is_public, share_with_users):
        """Load FASTA database file"""
        fasta_db = ProteinFastaDatabase.objects.create(
            name=file_name,
            user=user,
            is_public=is_public
        )
        with open(file_path, 'rb') as f:
            fasta_db.fasta_file.save(Path(file_path).name, File(f))
        if share_with_users:
            fasta_db.shared_with.set(share_with_users)
        fasta_db.save()
        visibility = 'public' if is_public else 'private'
        shared_info = f', shared with {len(share_with_users)} users' if share_with_users else ''
        self.stdout.write(self.style.SUCCESS(
            f'Successfully loaded FASTA database "{file_name}" (ID: {fasta_db.id}) for user {user.username} ({visibility}{shared_info})'
        ))

    def _load_pdb(self, file_path, file_name, user, chains, is_public, share_with_users):
        """Load PDB structure file"""
        structure = StructureFile.objects.create(
            name=file_name,
            user=user,
            chains=chains,
            is_public=is_public
        )
        with open(file_path, 'rb') as f:
            structure.structure_file.save(Path(file_path).name, File(f))
        if share_with_users:
            structure.shared_with.set(share_with_users)
        structure.save()
        visibility = 'public' if is_public else 'private'
        shared_info = f', shared with {len(share_with_users)} users' if share_with_users else ''
        self.stdout.write(self.style.SUCCESS(
            f'Successfully loaded PDB structure "{file_name}" (ID: {structure.id}) for user {user.username} ({visibility}{shared_info})'
        ))

    def _load_msa(self, file_path, file_name, user, is_public, share_with_users):
        """Load Multiple Sequence Alignment file"""
        msa = MultipleSequenceAlignment.objects.create(
            name=file_name,
            user=user,
            is_public=is_public
        )
        with open(file_path, 'rb') as f:
            msa.msa_file.save(Path(file_path).name, File(f))
        if share_with_users:
            msa.shared_with.set(share_with_users)
        msa.save()
        visibility = 'public' if is_public else 'private'
        shared_info = f', shared with {len(share_with_users)} users' if share_with_users else ''
        self.stdout.write(self.style.SUCCESS(
            f'Successfully loaded MSA "{file_name}" (ID: {msa.id}) for user {user.username} ({visibility}{shared_info})'
        ))
