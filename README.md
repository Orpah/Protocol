ORPAH Protocol
==============

The ORPAH protocol is a simple Wi-Fi 802.11b based protocol developed exclusively for ORPAH.

The ORPAH protocol involves one or many clients, one or many Wi-Fi routers and one server.
The main flow is: a client sends a signal to a Wi-Fi router without authentication, the router can forward the signal to a server.


## Why ORPAH?
ORPAH is designed to trace trafficking of children, disorientation of people because of Alzheimer's disease or etc.

### Differences from mobile phone tracking
Mobile phone tracking refers to the ascertaining of the position of a mobile phone, whether stationary or moving. Localization may occur either via multilateration of radio signals between (several) radio towers of the network and the phone, or simply via GPS. To locate the phone using multilateration of radio signals, it must emit at least the roaming signal to contact the next nearby antenna tower. The prerequisites of mobile phone tracking are the person has a mobile phone and the phone has power or is powered on. Is this difficult for ORPAH's target people? Yes, it is so easy for an infant or an Alzheimer's disease patient to forget to take/charge/turn on a mobile phone, that's why we have to create the ORPAH. ORPAH can support battery-free devices as clients, the devices can be put into necklace, glasses, buttons, shoes and etc.

### Differences from AMBER Alert
AMBER Alert is used in United States to find an abducted child at risk for serious bodily harm or death. The number of child trafficking in US is very low if compared with developing countries, so the AMBER Alert is not perfect for most cases in these areas, it may cause children's death instead of rescue. ORPAH is more suitable for tracing a child.


## ORPAH Message Flow
### ORPAH Network Structure
<img src="https://raw.github.com/orpah/protocol/master/docs/images/orpah_network_structure.png" width=600"/>

### ORPAH Message Flow between a client and a Wi-Fi router
<img src="https://raw.github.com/orpah/protocol/master/docs/images/orpah_flow_client_router.png" width=600"/>

### ORPAH Message Flow between a Wi-Fi router and an ORPAH server
<img src="https://raw.github.com/orpah/protocol/master/docs/images/orpah_flow_router_server.png" width=600"/>


## ORPAH Wi-Fi Router
### Why Wi-Fi?
Wi-Fi, Bluetooth and ZigBee are wireless protocols we can choose, among them, Wi-Fi is the most possible protocol to connect internet and send ORPAH signals to an ORPAH server, so we make ORPAH based on Wi-Fi.

### Why Wi-Fi 802.11b?
Wi-Fi 802.11b has the lowest data rate(1Mb/s), so it can cover a large range outdoor with the lowest power consumption. It's not supported by Wi-Fi Direct, this makes us easy to extend Wi-Fi 802.11b to support Wi-Fi ORPAH.

### Wi-Fi ORPAH
Wi-Fi ORPAH is a soft extension to Wi-Fi router OS which allow ORPAH clients to send ORPAH signals through a Wi-Fi router without authentication.


## ORAPAH Clients
ORPAH clients can be an APP on a mobile phone or a battery-free device.

### Battery-Free Device
#### Human-Motion-Powered Device
<img src="https://raw.github.com/orpah/protocol/master/docs/images/human_motion_powered_device.png" width=600"/>

#### Radio-Wave-Powered Device
<img src="https://raw.github.com/orpah/protocol/master/docs/images/radio_wave_powered_device.png" width=600"/>

### ORPAH APP
ORPAH APP can be extended to support more functions than battery-free device, such as opening mobile phone's GPS and sending GPS data to ORPAH server.


## References
##### Trafficking of children
[Trafficking of children on WikiPedia](https://en.wikipedia.org/wiki/Trafficking_of_children)

##### Alzheimer's disease
[Alzheimer's disease on WikiPedia](https://en.wikipedia.org/wiki/Alzheimer%27s_disease)

##### Mobile phone tracking
[Mobile phone tracking on WikiPedia](https://en.wikipedia.org/wiki/Mobile_phone_tracking)

##### AMBER Alert
[AMBER Alert Official Site](http://www.amberalert.gov/)

[AMBER Alert on WikiPedia](https://en.wikipedia.org/wiki/AMBER_Alert)

##### Ambient Backscatter
[Ambient Backscatter Official Site](http://abc.cs.washington.edu/)

[Ambient Backscatter on WikiPedia](https://en.wikipedia.org/wiki/Ambient_backscatter)

##### Wi-Fi 802.11b
[Wi-Fi 802.11b on WikiPedia](https://en.wikipedia.org/wiki/IEEE_802.11#802.11b)

##### Wi-Fi Direct
[Wi-Fi Direct on WikiPedia](https://en.wikipedia.org/wiki/Wi-Fi_Direct)

##### Bluetooth
[Bluetooth on WikiPedia](https://en.wikipedia.org/wiki/Bluetooth)

##### ZigBee
[ZigBee on WikiPedia](https://en.wikipedia.org/wiki/ZigBee)
