from requests import Session
from typing import get_args, Literal, NotRequired, TypedDict
import re


class RealIPConfigFilterCountry(TypedDict):
    exclude: NotRequired[list[str]]
    include: NotRequired[list[str]]


class RealIPConfigFilter(TypedDict):
    token: str
    country: RealIPConfigFilterCountry


RealIPConfigSource = Literal["cloudfront", "cloudflare", "gcore"]


class RealIPConfig(TypedDict):
    source: list[RealIPConfigSource]
    filter: NotRequired[RealIPConfigFilter]
    destination: str


class RealIPGetResult(TypedDict):
    header: str
    ips: list[str]


class RealIP:
    def __init__(self, config: RealIPConfig) -> None:
        for source in config["source"]:
            assert source in get_args(RealIPConfigSource)
        self.source = config["source"]
        self.destination = config["destination"]
        self._session = Session()
        if "filter" in config:
            self._session_headers = {
                "Authorization": "Bearer {}".format(config["filter"]["token"])
            }

            filter_re = ""
            if "include" in config["filter"]["country"]:
                filter_re += "(?={})".format(
                    "|".join(config["filter"]["country"]["include"])
                )
            if "exclude" in config["filter"]["country"]:
                filter_re += "(?!{})".format(
                    "|".join(config["filter"]["country"]["exclude"])
                )
            filter_re += ".+"
            self._filter_re = re.compile(filter_re)
            self.filter = lambda ip: (
                True
                if self._filter_re.match(
                    self._session.get(
                        "https://api.ipinfo.io/lite/{}".format(ip.split("/")[0]),
                        headers=self._session_headers,
                    ).json()["country_code"]
                )
                else False
            )
        else:
            self.filter = lambda ip: True
        pass

    def get_cloudflare(self) -> RealIPGetResult:
        response = self._session.get("https://api.cloudflare.com/client/v4/ips").json()

        return {
            "header": "CF-Connecting-IP",
            "ips": [
                *response["result"]["ipv6_cidrs"],
                *response["result"]["ipv4_cidrs"],
            ],
        }

    def get_cloudfront(self) -> RealIPGetResult:
        response = self._session.get(
            "https://ip-ranges.amazonaws.com/ip-ranges.json"
        ).json()

        return {
            "header": "CloudFront-Viewer-Address",
            "ips": [
                *[
                    ip["ipv6_prefix"]
                    for ip in response["ipv6_prefixes"]
                    if ip["service"] == "CLOUDFRONT_ORIGIN_FACING"
                ],
                *[
                    ip["ip_prefix"]
                    for ip in response["prefixes"]
                    if ip["service"] == "CLOUDFRONT_ORIGIN_FACING"
                ],
            ],
        }

    def get_gcore(self) -> RealIPGetResult:
        response = self._session.get("https://api.gcore.com/cdn/public-ip-list").json()

        return {
            "header": "X-Forwarded-For",
            "ips": [*response["addresses_v6"], *response["addresses"]],
        }

    def run(self):
        length = len(self.source)
        if length == 1:
            self.run_single()
        elif length > 1:
            self.run_multiple()
        else:
            raise IndexError("Source must has at least one item")

    def run_single(self):
        with open("{}/real_ip.conf".format(self.destination), "w") as f:
            method = getattr(self, "get_{}".format(self.source[0]))
            result: RealIPGetResult = method()
            for ip in result["ips"]:
                if self.filter(ip):
                    f.write("set_real_ip_from {};\n".format(ip))
            f.write("real_ip_header {};\n".format(result["header"]))

    def run_multiple(self):
        realip = open("{}/real_ip.conf".format(self.destination), "w")
        realip_multiple_headers = open(
            "{}/real_ip_multiple_headers.conf".format(self.destination), "w"
        )

        normalized_headers = []
        for index, source in enumerate(self.source):
            method = getattr(self, "get_{}".format(source))
            result: RealIPGetResult = method()

            normalized_headers.append(result["header"].replace("-", "_").lower())
            realip_multiple_headers.write(
                "geo $realip_remote_addr $with_{} {{\n    default 0;\n".format(
                    normalized_headers[index]
                )
            )
            for ip in result["ips"]:
                if self.filter(ip):
                    realip.write("set_real_ip_from {};\n".format(ip))
                    realip_multiple_headers.write("    {} 1;\n".format(ip))
            realip_multiple_headers.write("}\n")

        realip_multiple_headers.write(
            'map "{}" $real_ip {{\n'.format(
                ":".join(["$with_{}".format(h) for h in normalized_headers])
            )
        )
        entries = ["1" if i == 0 else "0" for i, _ in enumerate(normalized_headers)]
        for header in normalized_headers:
            realip_multiple_headers.write(
                '    "{}" $http_{};\n'.format(":".join(entries), header)
            )
            entries.insert(0, entries.pop())
        realip_multiple_headers.write(
            '}\nmore_set_input_headers "X-Real-IP: $real_ip";\nreal_ip_header X-Real-IP;\n'
        )

        realip.close()
        realip_multiple_headers.close()
