# neuView dataset configuration

Each `config.<dataset>.yaml` file configures one NeuPrint dataset (server,
dataset name, output, discovery, neuroglancer template, HTML metadata, subsets).
This document describes the optional **`hide_features`** block and the optional
**`neuroglancer.download_formats`** list.

## `hide_features`

Hide individual sections of the neuron pages and individual filters of the
types list, per dataset.

```yaml
hide_features:
  neuron: ["visualization"]
  nav: ["github", "youtube"]
  list: ["dimorphism", "hemilineage"]
```

**Semantics — listed means hidden.** Anything you list is hidden; anything you
do not list stays visible. A missing block, a missing key, or an empty list
therefore shows *as much as possible*:

| Config | Result |
| --- | --- |
| no `hide_features` block | everything visible |
| `neuron: []` (or key absent) | all neuron sections visible |
| `neuron: ["connectivity"]` | every neuron section **except** connectivity |

Unknown names are ignored with a warning (logged once per run), so a typo
disables nothing silently — check the logs if a feature you expected to hide is
still showing.

When a feature is hidden its **data is removed** from the page, not just hidden
with CSS: the section/filter and its supporting data (e.g. the matching tags on
the type cards, the hamburger-menu link) are not rendered.

### `neuron:` — sections of an individual neuron page

| Key | Hides |
| --- | --- |
| `cards` | Summary statistics cards (counts, synapses, …) |
| `layers` | "Mean Synapse Count per Layer" section |
| `eyemaps` | "Population Spatial Coverage" hexagon maps |
| `neuroglancer` | "Neuron Visualization" (embedded Neuroglancer) |
| `innervation` | "ROI Innervation" section |
| `connectivity` | Upstream/downstream connectivity tables |

Group shortcut (expands to several keys):

| Group | Expands to |
| --- | --- |
| `visualization` | `eyemaps`, `neuroglancer` |

### `nav:` — external service links

Hides every link to the named service across **all** pages (header bar,
hamburger menu, the GitHub feedback button, the per-neuron neuPrint link, the
per-neuron YouTube video link, and the contextual links on the index/help
pages). Prose mentions of the service name are kept; only the hyperlinks are
removed.

| Key | Hides links to |
| --- | --- |
| `github` | GitHub repository links + the feedback button (opens a GitHub issue) |
| `youtube` | YouTube channel link + per-neuron video links |
| `neuprint` | NeuPrint dataset links + the per-neuron "open in neuPrint" link |

### `list:` — filters/tags of the types list page

Each key hides both the filter dropdown and the matching tag on the type cards.

| Key | Hides |
| --- | --- |
| `roi` | ROI (brain region) filter + ROI tags |
| `neurotransmitter` | Neurotransmitter filter + NT tag |
| `dimorphism` | Dimorphism filter + tag |
| `side` | Side filter + the "only L/R/M / Undefined" indicators |
| `superclass` | Superclass filter + tag |
| `class` | Class filter + tag |
| `subclass` | Subclass filter + tag |
| `region` | Region filter + parent-region tags |
| `count` | Cell-count filter + count tag |
| `neuromere` | Soma-neuromere filter + tag |
| `hemilineage` | Truman-hemilineage filter + tag |

Note: hiding `side` or `count` removes only the *filter and tags*; the per-side
page links and cell-count totals shown in card titles/tooltips are core
navigation and remain.

### Example

```yaml
# A visual-system dataset that has no dimorphism or hemilineage annotation
# and no embedded Neuroglancer view:
hide_features:
  neuron: ["neuroglancer"]
  list: ["dimorphism", "hemilineage", "neuromere"]
```

## `neuroglancer.download_formats`

Offer per-neuron file downloads (skeletons, meshes) from the neuron pages. When
the list has at least one entry, the "Neuron Visualization" header shows a
download icon that opens a dialog with one radio button per format. The dialog
fetches one file per displayed neuron and saves them as a single zip archive.
When the list is missing or empty, neither the icon nor the dialog is rendered.

```yaml
neuroglancer:
  base_url: "https://neuroglancer-demo.appspot.com/"
  template: "neuroglancer-cns.js.jinja"
  download_formats:
    - key: swc
      label: "SWC skeleton (coarse)"
      kind: swc
      url_template: "https://www.googleapis.com/storage/v1/b/flyem-male-cns/o/v1.0%2Fsegmentation%2Fskeletons-malecns%2Fskeletons-swc%2F{body_id}.swc?alt=media"
    - key: obj
      label: "OBJ mesh"
      kind: ngmesh
      url_template: "https://www.googleapis.com/storage/v1/b/flyem-male-cns/o/v1.0%2Fsegmentation%2Fsingle-res-meshes%2F{body_id}:0?alt=media"
```

| Field | Required | Meaning |
|---|---|---|
| `key` | yes | Unique identifier; also used in the zip file name (`<type>_<key>.zip`) |
| `label` | yes | Text of the radio button in the dialog |
| `url_template` | yes | URL with a `{body_id}` placeholder; one request per neuron |
| `kind` | no (default `swc`) | `swc` or `ngmesh`, see below |

Kinds:

| Kind | File in the zip | Behavior |
|---|---|---|
| `swc` | `<body_id>.swc` | The response is stored verbatim. Works for any text or binary per-neuron file, not only SWC |
| `ngmesh` | `<body_id>.obj` | `url_template` must address the Neuroglancer legacy mesh manifest `<body_id>:0`. The fragments it lists are fetched from the same directory and converted to Wavefront OBJ in the browser (vertices in nanometers) |

Requirements and notes:

- The host must send CORS headers, because the browser fetches the files from
  the neuView page's origin (or from `file://`). For Google Cloud Storage use
  the JSON API form shown above; the plain
  `https://storage.googleapis.com/<bucket>/<object>` URL does not send them.
  Object paths in the JSON API form are URL-encoded (`/` becomes `%2F`).
- Configuration loading fails with a clear error if `{body_id}` is missing, the
  `kind` is unknown, or two entries share a `key`.
- The first entry is preselected. Order the list from cheapest to largest
  download; mesh files are roughly a hundred times larger than coarse SWC files.
- Selections above 50 neurons ask the user for confirmation. Neurons without a
  file are listed in `missing_body_ids.txt` inside the zip.
- The page only knows the neurons it sent to the viewer. Selections changed
  inside Neuroglancer can be downloaded by pasting the viewer URL into the
  dialog.
