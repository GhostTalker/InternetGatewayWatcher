# InternetGatewayWatcher
This script restarts the port of a UNIFI Switch if internet is not responding

#### Install:
```
local Raspi or server:
- pip3 install -r requirements.txt
- copy config.ini.example to config.ini and adjust the values
- run as python script like 'python3 igw.py'
```

#### PROMETHEUS CONFIG:
Use IP address of the device where IGW is running and PORT is configured in the config.ini
```
  - job_name: 'igw'
    scrape_interval: 10s
    static_configs:
      - targets: ['<IP>:<Port>']
```

#### Features and supported hardware:
```
- Grafana template added
- Prometheus metrics
- support for Unifi devices
```

## License
See the [LICENSE](https://github.com/GhostTalker/InternetGatewayWatcher/blob/master/LICENSE.md) file for license rights and limitations (MIT).
