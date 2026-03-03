# nginx-realip-generator

## Config

```json
{
    "#source#": "Put one or more CDN services, if more than one services are defined, additional workaround config is generated.",
    "source": [
        "cloudfront",
        "cloudflare",
        "gcore"
    ],
    "#filter#": "Remove to disable or fill the block to enable filtering out unnecessary IPs, like China servers of CloudFront.",
    "filter": {
        "#token#": "IPinfo Lite API token",
        "token": "",
        "#country#": "Use two letter country code to exclude or include unnecessary IPs.",
        "country": {
            "exclude": [],
            "include": []
        }
    },
    "#destination#": "Put destination folder for config, usually /etc/nginx/conf.d",
    "destination": "/tmp"
}

```
