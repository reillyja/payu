"""Functions to support Slurm scheduling.

:copyright: Copyright 2011 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""

# Standard library
import os
import re
import sys
import shlex
import subprocess

from payu.fsops import check_exe_path
from payu.schedulers.scheduler import Scheduler


class Slurm(Scheduler):
    # TODO: __init__

    def submit(self, pbs_script, pbs_config, pbs_vars=None, python_exe=None):
        """Prepare a correct PBS command string"""

        if python_exe is None:
            python_exe = sys.executable

        if pbs_vars is None:
            pbs_vars = {}

        # Set all environment variables which are propagated to the job
        #env_kv = [f'{k}={shlex.quote(v)}' for k, v in pbs_vars.items() if v is not None]
        #export_arg = 'ALL' + (',' + ','.join(env_kv) if env_kv else '')

        os.environ.update(
            dict(map(lambda kv: (kv[0], str(kv[1])), pbs_vars.items()))
        )
        
        os.environ.update({k: str(v) for k, v in pbs_vars.items() if v is not None})

        payu_path = pbs_vars.get('PAYU_PATH', os.path.dirname(sys.argv[0]))
        pbs_script = check_exe_path(payu_path, pbs_script)

        pbs_flags = []
        nnodes = pbs_config.get('nnodes')
        ncpus  = pbs_config.get('ncpus')
        ntasks_per_node = int(ncpus/nnodes)

        pbs_project = pbs_config.get('project')
        #pbs_project = pbs_config.get('project', os.environ['PROJECT'])
        pbs_flags.append('-A {project}'.format(project=pbs_project))
        pbs_flags.append('--time={}'.format(pbs_config.get('walltime')))
        pbs_flags.append('--ntasks={}'.format(pbs_config.get('ncpus')))
        #pbs_flags.append('--nodes={}'.format(pbs_config.get('nnodes')))
        pbs_flags.append('--exclusive')

        #pbs_flags.append('--ntasks-per-node={}'.format(ntasks_per_node))
        #pbs_flags.append('--mem=172g')
        #pbs_flags.append('')
        # Flags which need to be addressed
        # pbs_flags.append('--qos=debug')
        # pbs_flags.append('--cluster=c4')
        #print(f'pbs_vars: {pbs_vars}')
        
     #   if '--mpi=pmix' not in pbs_flags:
     #       pbs_flags.append('--mpi=pmix')


        mods = pbs_config.get('modules')
        print(f'Modules from config are: {mods}')
        
        module_cmds = 'module purge; ' + ' ; '.join(f'module load {m}' for m in mods)

        # Strip any Spack/OpenMPI/libfabric paths that might shadow Cray libs
        sanitize = r'''
        _keep=""
        IFS=: read -ra arr <<< "${LD_LIBRARY_PATH:-}"
        for p in "${arr[@]}"; do
            case "$p" in
            *"/software/setonix/"*"/libfabric"*|*"/software/setonix/"*"/openmpi"*) : ;;
             *) _keep="${_keep:+$_keep:}$p" ;;
            esac
        done
        export LD_LIBRARY_PATH="$_keep"
        unset FI_PROVIDER_PATH
        '''

        # Build the payload to run on the compute node
        payload = f'''{module_cmds};
        {sanitize}
        export FI_PROVIDER=cxi
        export MPICH_OFI_NIC_POLICY=NIC
        export LD_LIBRARY_PATH="${{LIBFABRIC_DIR:+$LIBFABRIC_DIR/lib64:}}$LD_LIBRARY_PATH"
        exec {shlex.quote(python_exe)} {shlex.quote(pbs_script)}
        '''

        wrap = f'bash -lc {shlex.quote(payload)}'

        export_items = [f'{k}={shlex.quote(str(v))}' for k, v in pbs_vars.items() if v is not None]
        export_arg = 'ALL' + (',' + ','.join(export_items) if export_items else '')

        cmd = f'sbatch {" ".join(pbs_flags)} --export={export_arg} --wrap={wrap}'

        # Construct job submission command
      #  cmd = 'sbatch {flags} --wrap="{python} {script}" --export="{envs}"'.format(
     #       flags=' '.join(pbs_flags),
    #        python=python_exe,
   #         script=pbs_script,
  #         # exports=export_arg
 #           envs=",".join(["{}={}".format(k, v) for k, v in pbs_vars.items()])
#        )
        print(cmd)
        #dsa
        return cmd
