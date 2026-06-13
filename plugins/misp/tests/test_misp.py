MISP_RESPONSE = {
    "Attribute": [
        {
            "id": "82741",
            "event_id": "305",
            "category": "Payload delivery",
            "type": "ip-src",
            "comment": "C2 beacon observed during Cobalt Strike campaign",
            "value": "198.51.100.42",
            "threat_level_id": "1",
            "Sighting": [
                {
                    "id": "12",
                    "type": "0",
                    "date_sighting": "1749123600",
                    "Organisation": {"name": "Acme SOC"}
                },
                {
                    "id": "13",
                    "type": "0",
                    "date_sighting": "1749210000",
                    "Organisation": {"name": "Acme SOC"}
                }
            ],
            "Event": {
                "id": "305",
                "info": "Stop Ransomware: Medusa Ransomware",
                "date": "2026-06-01",
                "threat_level_id": "1",
                "Org": {"name": "Acme SOC"},
                "Orgc": {"name": "Threat Intel Team"}
            },
            "Tag": [
                {"name": "kill-chain:Command and Control", "colour": "#a80079"},
                {"name": "adversary:infrastructure-type=\"C2\"", "colour": "#ff6600"},
                {"name": "tlp:green", "colour": "#00cc00"}
            ]
        }
    ]
}
