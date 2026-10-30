#!/usr/bin/env python3
"""Exercise the public skills CLI in a disposable project, without global installs."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    env = dict(os.environ, DISABLE_TELEMETRY='1', DO_NOT_TRACK='1')
    with tempfile.TemporaryDirectory(prefix='video-skills-npx-') as directory:
        root = Path(directory)
        subprocess.run(['npx', '--yes', 'skills@latest', 'add', args.source,
                        '--skill', '*', '--agent', 'codex', '-y'],
                       cwd=root, env=env, check=True, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, text=True)
        skills = root / '.agents/skills'
        names = sorted(p.name for p in skills.glob('video-*') if (p/'SKILL.md').is_file())
        if len(names) != 12:
            raise RuntimeError(f'Expected 12 skills, got {names}')
        for name in names:
            assert (skills/name/'LICENSE').is_file(), name
            assert (skills/name/'references/integration.md').is_file(), name
        assert (skills/'video-write/references/shanyin/LICENSE').is_file()
        tool = skills/'video-produce/scripts/workflow.py'
        project = root/'作品'
        subprocess.run([sys.executable, str(tool), 'init', str(project), '--title', '安装烟测'],
                       check=True, stdout=subprocess.PIPE, text=True)
        output = subprocess.check_output([sys.executable, str(tool), 'resume', str(project)], text=True)
        report = json.loads(output)
        assert report['read_only'] and report['next_actions'][0]['skill'] == 'video-develop'
        print(json.dumps({'source':args.source, 'skills':names, 'init':'passed',
                          'resume':'passed', 'global_install':False}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
