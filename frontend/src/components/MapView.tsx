"use client";

import "leaflet/dist/leaflet.css";
import "leaflet.markercluster/dist/MarkerCluster.css";
import "leaflet.markercluster/dist/MarkerCluster.Default.css";
import L from "leaflet";
import { useEffect, useMemo, useRef } from "react";
import { Circle, MapContainer, Marker, Polyline, Popup, TileLayer, Tooltip, useMap } from "react-leaflet";
import MarkerClusterGroup from "react-leaflet-cluster";
import type { Spot } from "@/lib/types";

const NYC_CENTER: [number, number] = [40.7295, -73.9965];
const MAP_ACCENT_BLUE = "#4285f4";
const MAP_ACCENT_GREEN = "#34a853";
const MAP_ACCENT_AMBER = "#fbbc05";
const MILES_TO_METERS = 1609.34;

function dotIcon(color: string, size = 14) {
  return L.divIcon({
    html: `<div style="width:${size}px;height:${size}px;border-radius:50%;background:${color};border:2px solid #202124;box-shadow:0 1px 2px rgba(0,0,0,0.5);"></div>`,
    className: "", // strip Leaflet's default marker-icon classes/background
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

function anchorIcon() {
  return L.divIcon({
    html: `<div style="width:26px;height:26px;border-radius:50% 50% 50% 0;background:${MAP_ACCENT_AMBER};border:2px solid #202124;transform:rotate(-45deg);box-shadow:0 1px 3px rgba(0,0,0,0.6);"></div>`,
    className: "",
    iconSize: [26, 26],
    iconAnchor: [13, 26],
  });
}

const savedIcon = dotIcon(MAP_ACCENT_BLUE);
const fallbackIcon = dotIcon(MAP_ACCENT_GREEN);
const savedIconSelected = dotIcon(MAP_ACCENT_BLUE, 22);
const fallbackIconSelected = dotIcon(MAP_ACCENT_GREEN, 22);
const homeIcon = anchorIcon();

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

function FlyToSelected({
  spot,
  markerRefs,
}: {
  spot: Spot | undefined;
  markerRefs: React.MutableRefObject<Record<string, L.Marker | null>>;
}) {
  const map = useMap();
  useEffect(() => {
    if (!spot || spot.coordinates.lat == null || spot.coordinates.lng == null) return;
    const target: [number, number] = [spot.coordinates.lat, spot.coordinates.lng];
    map.flyTo(target, Math.max(map.getZoom(), 15), { duration: 0.6 });
    const marker = markerRefs.current[spot.id];
    if (marker) {
      window.setTimeout(() => marker.openPopup(), 350);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [spot, map]);
  return null;
}

export function MapView({
  spots,
  anchor,
  radiusMiles,
  itineraryStops,
  selectedSpotId,
  onSelectSpot,
}: {
  spots: Spot[];
  anchor?: { lat: number; lng: number; label: string } | null;
  radiusMiles?: number | null;
  itineraryStops?: { lat: number; lng: number }[];
  selectedSpotId?: string | null;
  onSelectSpot?: (id: string | null) => void;
}) {
  const plottable = useMemo(
    () => spots.filter((s) => s.coordinates.lat != null && s.coordinates.lng != null),
    [spots],
  );
  const markerRefs = useRef<Record<string, L.Marker | null>>({});
  const selectedSpot = plottable.find((s) => s.id === selectedSpotId);
  const polylinePositions = useMemo(
    () => (itineraryStops ?? []).map((s) => [s.lat, s.lng] as [number, number]),
    [itineraryStops],
  );

  return (
    <div className="relative rounded-lg overflow-hidden border border-border h-[560px]">
      <MapContainer center={NYC_CENTER} zoom={12} className="h-full w-full" scrollWheelZoom>
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        />

        {anchor && (
          <>
            <Marker position={[anchor.lat, anchor.lng]} icon={homeIcon} zIndexOffset={1000}>
              <Tooltip>{anchor.label}</Tooltip>
            </Marker>
            {radiusMiles != null && (
              <Circle
                center={[anchor.lat, anchor.lng]}
                radius={radiusMiles * MILES_TO_METERS}
                pathOptions={{ color: MAP_ACCENT_AMBER, fillOpacity: 0.06, weight: 1.5 }}
              />
            )}
          </>
        )}

        {polylinePositions.length > 1 && (
          <Polyline positions={polylinePositions} pathOptions={{ color: MAP_ACCENT_BLUE, weight: 2, dashArray: "6 6" }} />
        )}

        <MarkerClusterGroup chunkedLoading>
          {plottable.map((spot) => {
            const isSelected = spot.id === selectedSpotId;
            const icon =
              spot.source === "saved"
                ? isSelected
                  ? savedIconSelected
                  : savedIcon
                : isSelected
                  ? fallbackIconSelected
                  : fallbackIcon;
            return (
              <Marker
                key={spot.id}
                position={[spot.coordinates.lat as number, spot.coordinates.lng as number]}
                icon={icon}
                ref={(ref) => {
                  markerRefs.current[spot.id] = ref;
                }}
                eventHandlers={{ click: () => onSelectSpot?.(spot.id) }}
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
            );
          })}
        </MarkerClusterGroup>
        <FitBounds spots={plottable} />
        <FlyToSelected spot={selectedSpot} markerRefs={markerRefs} />
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
        {anchor && (
          <div className="flex items-center gap-1.5 mt-1">
            <span className="size-2.5 rounded-full" style={{ background: MAP_ACCENT_AMBER }} />
            Anchor
          </div>
        )}
      </div>
    </div>
  );
}
