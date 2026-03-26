# Exeter Town Map — Recon Summary

Source: https://www.mapsonline.net/exeternh/

## Platform

- **PeopleGIS SimpliCITY** (MO4 variant)
- **Map library**: OpenLayers 2.13.1 (bundled as `ol-mo4-2.13.1.min.js`)
- **JS globals**: `MO4` (app), `OpenLayers` (OL2), `MO4.map` (map instance)
- **Projection (map)**: EPSG:900913 (Web Mercator)
- **Projection (client/data)**: EPSG:3437 (NH State Plane, NAD83, feet)
- **proj4js** loaded in-page for coordinate transforms
- **Disclaimer popup** must be dismissed before map is interactive

## WMS Backend

```
Endpoint: https://www.mapsonline.net/cgi-bin/mapserv
Mapfile:  /home/peoplegis/mapsonline/exeternh/map/mo4/mo4_site_207.map
Service:  WMS 1.1.1 (MapServer)
Format:   image/png (TRANSPARENT=TRUE)
SRS:      EPSG:900913
```

### Example GetMap request

```
GET https://www.mapsonline.net/cgi-bin/mapserv
  ?map=/home/peoplegis/mapsonline/exeternh/map/mo4/mo4_site_207.map
  &SERVICE=WMS
  &VERSION=1.1.1
  &REQUEST=GetMap
  &LAYERS=site_207::Parcels for Identify
  &STYLES=
  &FORMAT=image/png
  &SRS=EPSG:900913
  &TRANSPARENT=TRUE
  &BBOX=-7902659.54,5309533.81,-7901401.20,5310236.08
  &WIDTH=2107
  &HEIGHT=1176
```

### GetFeatureInfo (to extract parcel attributes + geometry)

```
GET https://www.mapsonline.net/cgi-bin/mapserv
  ?map=/home/peoplegis/mapsonline/exeternh/map/mo4/mo4_site_207.map
  &SERVICE=WMS
  &VERSION=1.1.1
  &REQUEST=GetFeatureInfo
  &LAYERS=site_207::Parcels for Identify
  &QUERY_LAYERS=site_207::Parcels for Identify
  &SRS=EPSG:900913
  &BBOX=<bbox>
  &WIDTH=800
  &HEIGHT=600
  &X=400
  &Y=300
  &INFO_FORMAT=application/json
  &FEATURE_COUNT=10
```

## Base Maps (5)

| Radio button label          | Type         | Tilecache name                  |
|-----------------------------|--------------|---------------------------------|
| OpenStreetMap               | External     | (OSM tiles)                     |
| Google Street Map           | External     | (Google Maps API)               |
| 2021/22 Aerial Photography  | WMS tilecache| `2021-22-aerial-photography`    |
| 2023 Aerial Photography     | WMS tilecache| `2023-aerials`                  |
| town-basemap-v2             | WMS tilecache| `town-basemap-v2`               |

### Aerial basemap sublayers (bundled in tilecache)

**2021/22 Aerial Photography** (sl_id: 178358):
- NH Highway Shields (3870), NH Highways (3869)
- Street Names (19678), Town Boundary (5451)
- Abutting Towns (4371), Hillshade Donut (5455)
- 2021/2022 Aerial Photos (35833)

**town-basemap-v2** (sl_id: 184538):
- Abutting Towns (35959), Transmission Lines (35938)
- NH Highways (3869/3870), Streets 2025 (37117)
- Trails (35935), Railroad (35933)
- Buildings 2025 (36972), Water (35937)
- Parks & Recreation (35934), Conservation Land 2025 (36971)
- ROW (35958), Town Boundary (35939), Hillshade Donut (5455)

## Overlay Layers

### Parcels (most relevant)

| Layer name              | layer_id | sl_id | Notes                        |
|-------------------------|----------|-------|------------------------------|
| Parcel Map Index        | 5456     | 9498  | Index sheets                 |
| **Parcels for Identify**| **5504** | **9499** | **Queryable, hidden** — this is the one for GetFeatureInfo |
| Parcel Numbers          | 11699    | 38932 | Labels                       |
| Parcels - Lot Dimensions| 35963    | 9466  | Tilecache: `parcels`         |
| Parcels (polygons)      | 4339     | 9466  | Tilecache: `parcels`         |

### Other overlays

| Group              | Layers                                                  |
|--------------------|---------------------------------------------------------|
| Address Numbers    | 5515                                                    |
| Historic Photos    | 4375 (queryable)                                        |
| ROW/Private Road   | 35061                                                   |
| Curbside Collection| Mon(35851) Tue(35852) Wed(35853) Thu(35854) Fri(35855)   |
| Sewer System       | Manholes(31105), Gravity Mains(31084)                   |
| Water System       | Hydrants labels(32544), Hydrants(31087), Mains(31083)   |
| Drainage           | Structures Label(23515), Structures(28458), Lines(28432)|
| MS4 Area           | 24569                                                   |
| Prime Wetlands     | 36744, 100ft buffer(36745)                              |
| FEMA Flood Zones   | 35873                                                   |
| Aquifers           | 4338 (codes 0-5)                                        |
| Wetlands           | Parcel Wetlands(4334)                                   |
| Historic District  | 36948                                                   |
| Zoning             | Labels(5514), Zones(4333, queryable) — 19 zone types    |
| Elevation          | 2ft contours(35841), 10ft contours(35840)               |
| Soils              | SSURGO(35864)                                           |

## JS API (for Playwright)

```js
// Map object
MO4.map                          // OpenLayers.Map instance
MO4.map.getCenter()              // {lon, lat} in EPSG:900913
MO4.map.getZoom()                // integer
MO4.map.getProjection()          // "EPSG:900913"

// Measure tools
MO4.measureControls.length       // line measurement control
MO4.measureControls.area         // area measurement control

// Projection transform (in-page)
const src = new OpenLayers.Projection('EPSG:900913');
const dst = new OpenLayers.Projection('EPSG:4326');
point.transform(src, dst);       // → WGS84 lat/lon

// Client projection (NH State Plane feet)
MO4.clientProjection             // EPSG:3437 with full proj4 def

// Layer control
MO4.getSiteLayerById(id)
MO4.turnOnSiteLayer(id)
MO4.turnOffSiteLayer(id)
MO4.isSiteLayerVisible(id)

// Identify (click-query)
MO4.multiIdentify               // function for feature identification
MO4.identifyControl             // OL2 identify control

// Parcel layer
MO4.map.getLayersByName('parcels')  // returns [OL2 Layer]
```

## Data extraction strategy

### Option A: Pure WMS (preferred — no browser needed)

1. `GetCapabilities` to confirm available layers and supported INFO_FORMAT
2. `GetFeatureInfo` on "Parcels for Identify" layer at property center point
3. Parse response for parcel polygon geometry + attributes
4. Reproject EPSG:3437 → WGS84 via pyproj
5. Submit to homemodel via ingestion pipeline

### Option B: Playwright + JS evaluation (fallback)

1. Navigate to map URL, dismiss disclaimer
2. `page.evaluate()` to access `MO4.map`, `MO4.measureControls`
3. Use `MO4.multiIdentify` to query parcels programmatically
4. Extract geometry from identify response
5. Transform coordinates via in-page proj4js
6. Submit to homemodel via ingestion pipeline

### Relevant layers for homemodel

| Town layer           | → homemodel entity type | Notes                     |
|----------------------|------------------------|---------------------------|
| Parcels for Identify | `feature` (boundary)   | Parcel polygon + lot dims |
| Parcels - Lot Dims   | `feature` (measurements)| Edge lengths in feet     |
| Elevation contours   | `terrain_patch`        | 2ft/10ft contour lines    |
| Buildings 2025       | `structure`            | Building footprints       |
| Wetlands             | `feature` (constraint) | Wetland boundaries        |
| Zoning               | `feature` (metadata)   | Zone classification       |
| FEMA Flood Zones     | `feature` (constraint) | Flood hazard areas        |
| Aerial Photography   | texture source         | For terrain textures      |
