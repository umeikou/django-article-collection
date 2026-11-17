"""Safe one-line adapter around the installed Xiaoyuzhou metadata parser."""
import argparse
import importlib.util
import json
import socket
import sys
import urllib.error

SAFE_CODES = {'metadata_network_timeout', 'metadata_platform_temporary', 'metadata_unavailable', 'metadata_invalid_response'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--episode-url', required=True)
    parser.add_argument('--skill-script', required=True)
    args = parser.parse_args()
    try:
        spec = importlib.util.spec_from_file_location('xiaoyuzhou_skill_fetch', args.skill_script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        metadata = module.parse(args.episode_url)
        if not isinstance(metadata, dict):
            raise ValueError()
        response = {'ok': True, 'metadata': metadata}
    except (socket.timeout, TimeoutError):
        response = {'ok': False, 'code': 'metadata_network_timeout', 'retryable': True}
    except (urllib.error.URLError, urllib.error.HTTPError):
        response = {'ok': False, 'code': 'metadata_platform_temporary', 'retryable': True}
    except SystemExit:
        response = {'ok': False, 'code': 'metadata_unavailable', 'retryable': False}
    except Exception:
        response = {'ok': False, 'code': 'metadata_invalid_response', 'retryable': False}
    sys.stdout.write(json.dumps(response, ensure_ascii=False, separators=(',', ':')) + '\n')

if __name__ == '__main__':
    main()
