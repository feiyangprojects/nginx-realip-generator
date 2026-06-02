#!/usr/bin/env python3
import argparse
import os
import utils
import json

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="generate config for ngx_http_realip_module"
    )
    parser.add_argument(
        "action",
        default="generate",
        choices=["generate", "generate-schema"],
        help="action to proceed",
    )
    args = parser.parse_args()

    root = os.path.dirname(os.path.realpath(__file__))

    if args.action == "generate":
        with open("{}/data/config.json".format(root), "r") as config:
            realip = utils.RealIP(json.load(config))

            realip.run()
    elif args.action == "generate-schema":
        from pydantic import TypeAdapter

        try:
            from pydantic import TypeAdapter
        except ImportError:
            print("You need to install development dependencies to generate schema!")
            exit(1)

        adapter = TypeAdapter(utils.RealIPConfig)
        json_schema = adapter.json_schema()
        with open("{}/data/examples/config.schema.json".format(root), "w") as schema:
            json.dump(json_schema, schema)
