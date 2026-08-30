"use client";

import "leaflet/dist/leaflet.css";
import "leaflet.markercluster/dist/MarkerCluster.css";
import "leaflet.markercluster/dist/MarkerCluster.Default.css";
import L from "leaflet";
import { useEffect, useMemo } from "react";
import { MapContainer, Marker, Popup, TileLayer, Tooltip, useMap } from "react-leaflet";
import MarkerClusterGroup from "react-leaflet-cluster";
import type { Spot } from "@/lib/types";

const NYC_CENTER: [number, number] = [40.7295, -73.9965];
const MAP_ACCENT_BLUE = "#4285f4";
const MAP_ACCENT_GREEN = "#34a853";

function dotIcon(color: string) {
  return L.divIcon({
    html: `<div style="width:14px;height:14px;border-radius:50%;background:${color};border:2px solid #202124;box-shadow:0 1px 2px rgba(0,0,0,0.5);"></div>`,
    className: "", // strip Leaflet's default marker-icon classes/background
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  });
}

const savedIcon = dotIcon(MAP_ACCENT_BLUE);
const fallbackIcon = dotIcon(MAP_ACCENT_GREEN);

function FitBounds({ spots }: { spots: Spot[] }) {
  const map = useMap();
  useEffect(() => {
    const coords = spots
      .filter((s) => s.coordinates.lat != null && s.coordinates.lng != null)
      .map((s) => [s.coordinates.lat as number, s.coordinates.lng as number] as [number, number]);
    if (coords.length > 1) {
      map.fitBounds(coords, { padding: [30, 30] });
    } else if (coords.length === 1) {
      map.setView(coords[0], 14);
    }
  }, [spots, map]);
  return null;
}

export function MapView({ spots }: { spots: Spot[] }) {
  const plottable = useMemo(
    () => spots.filter((s) => s.coordinates.lat != null && s.coordinates.lng != null),
    [spots],
  );

  return (
    <div className="relative rounded-lg overflow-hidden border border-border h-[560px]">
      <MapContainer center={NYC_CENTER} zoom={12} className="h-full w-full" scrollWheelZoom>
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        />
        <MarkerClusterGroup chunkedLoading>
          {plottable.map((spot) => (
            <Marker
              key={spot.id}
              position={[spot.coordinates.lat as number, spot.coordinates.lng as number]}
              icon={spot.source === "saved" ? savedIcon : fallbackIcon}
            >
              <Tooltip>{spot.name}</Tooltip>
              <Popup>
                <b>{spot.name}</b>
                <br />
                {spot.neighborhood}
                <br />
                {spot.match_highlight}
              </Popup>
            </Marker>
          ))}
        </MarkerClusterGroup>
        <FitBounds spots={plottable} />
      </MapContainer>

      {/* Floating legend, Google-Maps-style, overlaid in a map corner. */}
      <div className="absolute bottom-3 left-3 z-[1000] rounded-lg bg-background/90 px-3 py-2 text-xs shadow-md">
        <div className="flex items-center gap-1.5">
          <span className="size-2.5 rounded-full" style={{ background: MAP_ACCENT_BLUE }} />
          Saved spots
        </div>
        <div className="flex items-center gap-1.5 mt-1">
          <span className="size-2.5 rounded-full" style={{ background: MAP_ACCENT_GREEN }} />
          Fallback picks
        </div>
      </div>
    </div>
  );
}
