import pandas as pd
import streamlit as st
import folium
import requests
import polyline
from pathlib import Path

OSRM_URL = "http://router.project-osrm.org/route/v1/driving/"
SC_COORDS = (14.713214, -17.463984)


@st.cache_data # Cache the route data to avoid repeated API calls
def get_osrm_route(stops: pd.DataFrame) -> list[tuple[float, float]] | None:
    """
    Fetches a driving route from the OSRM API.
    Returns a list of (latitude, longitude) tuples representing the route.
    """
    coordinates = ';'.join([f"{lon},{lat}" for lat, lon in stops[["Latitude", "Longitude"]].values])
    url = f"{OSRM_URL}{coordinates}?overview=full&geometries=polyline"

    try:
        response = requests.get(url)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        data = response.json()

        if data and data['code'] == 'Ok' and data['routes']:
            encoded_polyline = data['routes'][0]['geometry']
            # Decode the polyline string into a list of (latitude, longitude) pairs
            decoded_route = polyline.decode(encoded_polyline)
            return decoded_route
        else:
            st.error(f"OSRM Error: {data.get('message', 'No route found or unexpected response.')}")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to OSRM: {e}")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return None
    

def add_route_to_map(plot: folium.Map, route_points: list[tuple[float, float]], route_stops: list[tuple[float, float, str]]) -> None:
    folium.Marker(
        location=route_points[0],
        # popup=f"<b>{route_stops[0][2]}</b>",
        tooltip=route_stops[0][2],
        icon=folium.Icon(color='green', icon='play', prefix='fa')
    ).add_to(plot)
    for point in route_stops[1:-1]:
        folium.Marker(
            location=point[:2],
            icon=folium.Icon(color='blue', icon='info-sign', prefix='fa'),
            tooltip=point[2]
        ).add_to(plot)
    # Add the PolyLine to highlight the road itinerary using OSRM data
    folium.PolyLine(
        locations=route_points, # Use the decoded points from OSRM
        color='blue',       # Color of the line
        weight=5,           # Thickness of the line
        opacity=0.5,        # Transparency of the line
        tooltip="Road Itinerary"
    ).add_to(plot)


def init_map() -> folium.Map:
    plot = folium.Map(location=SC_COORDS, zoom_start=12)
    folium.Marker(
        location=SC_COORDS,
        # popup="<b>Sacré Coeur</b>",
        tooltip="Sacré Coeur",
        icon=folium.Icon(color='red', icon='stop', prefix='fa')
    ).add_to(plot)
    return plot

def build_map():
    plot = init_map()
    routes_path = Path(__file__).parent / "routes"
    route_paths = list(routes_path.rglob("**/*.csv"))
    for route_path in route_paths:
        route_frame = pd.read_csv(route_path)
        osm_route = get_osrm_route(route_frame)
        if osm_route is None:
            st.error(f"Failed to fetch route for {route_path.name}.")
            continue
        add_route_to_map(plot, osm_route, route_frame.values.tolist())
    return plot


if __name__ == "__main__":
    plot = build_map()
    st.set_page_config(layout="wide")
    st.title("Bus Sacré Coeur")
    st.components.v1.html(plot._repr_html_(), height=600, scrolling=False)
    st.write(
        """
        Cette carte affiche les itinéraires des bus de Sacré Coeur.
        La liste des arrêts est extraite de fichiers CSV situés dans le répertoire `/routes`.
        Les itinéraires sont récupérés via l'API OSRM (Open Source Routing Machine).
        """
    )
