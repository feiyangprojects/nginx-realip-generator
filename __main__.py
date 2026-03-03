import utils
import json

if __name__ == "__main__":
    with open("data/config.json", "r") as config:
        realip = utils.RealIP(json.load(config))

        realip.run()
