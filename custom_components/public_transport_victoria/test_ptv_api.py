import asyncio
from PublicTransportVictoria.api.client import PTVApiClient
from PublicTransportVictoria.api.route_types import RouteTypesAPI
from PublicTransportVictoria.api.routes import RoutesAPI, RouteRequest
from PublicTransportVictoria.api.stops import StopsAPI, StopRequest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from collections import defaultdict


async def test_api():
    # Initialize Home Assistant with a config directory
    hass = HomeAssistant(config_dir="/workspaces/ha_core/config")

    # Set up the aiohttp session
    async_get_clientsession(hass)

    # Initialize the API client
    dev_id = "3002893"
    api_key = "7fb99ba4-1781-4f79-a089-d3c69229f57f"
    client = PTVApiClient(hass, dev_id, api_key)

    # Initialize the RouteTypesAPI and RoutesAPI
    route_types_api = RouteTypesAPI(client)
    routes_api = RoutesAPI(client)
    stops_api = StopsAPI(client)

    # Get all route types
    try:
        route_types_response = await route_types_api.get_route_types()
        route_types = route_types_response.get("route_types", [])
        print("Route Types:", route_types)
    except Exception as e:
        print("Error fetching route types:", e)
        return


async def collect_stations_by_route_type(routes_api, stops_api):
    stations_by_route_type = defaultdict(set)

    for route_type_id in range(5):  # Assuming route types are 0 to 4
        routes_response = await routes_api.get_routes_for_route_type(route_type_id)
        routes = routes_response.get("routes", [])

        if routes:
            for route in routes:
                stop_request = StopRequest(
                    route_id=route["route_id"], route_type=route_type_id
                )
                stops_response = await stops_api.get_stops_for_route(stop_request)
                stops = stops_response.get("stops", [])
                
                for stop in stops:
                    stations_by_route_type[route_type_id].add(stop['stop_name'])

                print(f"Processed Route: {route['route_name']} (Type: {route_type_id})")
                print(f"Added {len(stops)} stops")
                print("-" * 50)

    return stations_by_route_type



# Run the test
if __name__ == "__main__":
    asyncio.run(test_api())
    # # Usage
    stations_by_route_type = await collect_stations_by_route_type(routes_api, stops_api)

    # Print results
    route_type_names = {
        0: "Train",
        1: "Tram",
        2: "Bus",
        3: "Vline",
        4: "Night Bus"
    }

    for route_type, stations in stations_by_route_type.items():
        print(f"\n{route_type_names[route_type]} Stations ({len(stations)}):")
        for station in sorted(stations):
            print(f"- {station}")
        print("-" * 50)    
