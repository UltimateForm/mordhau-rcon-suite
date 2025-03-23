def get_killed_players_pipeline(playfab_id: str):
    return [
        {"$match": {"playfab_id": playfab_id}},
        {
            "$project": {
                "kills": {"$objectToArray": "$kills"},
                "killer_name": "$user_name",
            }
        },
        {"$unwind": {"path": "$kills"}},
        {
            "$lookup": {
                "from": "kills",
                "localField": "kills.k",
                "foreignField": "playfab_id",
                "as": "player",
            }
        },
        {"$unwind": {"path": "$player"}},
        {
            "$project": {
                "user_name": "$player.user_name",
                "playfab_id": "$player.playfab_id",
                "times_killed": "$kills.v",
                "killer_name": 1,
            }
        },
        {"$sort": {"times_killed": -1}},
    ]
