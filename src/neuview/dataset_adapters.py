"""
Dataset adapters for handling differences between NeuPrint datasets.

Different NeuPrint datasets (hemibrain, cns, optic-lobe) have varying
database structures and property names. These adapters normalize
the differences and provide a consistent interface.
"""

import re
import pandas as pd
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple, Type, Dict
from dataclasses import dataclass


@dataclass
class DatasetInfo:
    """Information about a dataset structure."""

    name: str
    soma_side_column: Optional[str] = None
    soma_side_extraction: Optional[str] = None  # regex pattern
    pre_synapse_column: str = "pre"
    post_synapse_column: str = "post"
    upstream_column: str = "upstream"
    downstream_column: str = "downstream"
    instance_column: str = "instance"
    type_column: str = "type"
    body_id_column: str = "bodyId"
    roi_columns: Optional[List[str]] = None

    def __post_init__(self):
        if self.roi_columns is None:
            self.roi_columns = ["inputRois", "outputRois"]


@dataclass
class RoiQueryStrategy(ABC):
    """Abstract base class for ROI query strategies."""

    @abstractmethod
    def get_central_brain_rois(self, all_rois: List[str]) -> List[str]:
        """Get list of ROIs that constitute the central brain for this dataset."""
        pass

    @abstractmethod
    def get_primary_rois(self, all_rois: List[str]) -> List[str]:
        """Get list of primary/main ROIs for this dataset."""
        pass

    @abstractmethod
    def categorize_rois(self, all_rois: List[str]) -> Dict[str, List[str]]:
        """Categorize ROIs into functional groups (e.g., visual, central, layers, columns)."""
        pass

    @abstractmethod
    def filter_rois_by_type(self, all_rois: List[str], roi_type: str) -> List[str]:
        """Filter ROIs by type (e.g., 'layers', 'columns', 'ROIs')."""
        pass


class CNSRoiQueryStrategy(RoiQueryStrategy):
    """ROI query strategy for CNS dataset."""

    def get_central_brain_rois(self, all_rois: List[str]) -> List[str]:
        """CNS has explicit centralBrain ROI."""
        return [roi for roi in all_rois if roi == "CentralBrain"]

    def get_primary_rois(self, all_rois: List[str]) -> List[str]:
        """Get primary ROIs for CNS."""
        primary_patterns = [
            r"^[A-Z]+\([LR]\)$",  # Standard ROI format like FB(R), PB(L)
            r"^[A-Z]+$",  # Simple ROI names
        ]
        excluded_rois = {"Optic(R)", "Optic(L)"}  # Exclude these from CNS ROI table

        primary_rois = []
        for roi in all_rois:
            if roi in excluded_rois:
                continue
            if any(re.match(pattern, roi) for pattern in primary_patterns):
                primary_rois.append(roi)
        return primary_rois

    def categorize_rois(self, all_rois: List[str]) -> Dict[str, List[str]]:
        """Categorize ROIs for CNS dataset."""
        categories = {
            "central_brain": self.get_central_brain_rois(all_rois),
            "primary_rois": self.get_primary_rois(all_rois),
            "layers": [],
            "columns": [],
            "other": [],
        }

        # Classify remaining ROIs
        categorized = set(categories["central_brain"] + categories["primary_rois"])
        for roi in all_rois:
            if roi not in categorized:
                categories["other"].append(roi)

        return categories

    def filter_rois_by_type(self, all_rois: List[str], roi_type: str) -> List[str]:
        """Filter ROIs by type for CNS."""
        if roi_type == "central_brain":
            return self.get_central_brain_rois(all_rois)
        elif roi_type == "primary":
            return self.get_primary_rois(all_rois)
        else:
            return []


class OpticLobeRoiQueryStrategy(RoiQueryStrategy):
    """ROI query strategy for Optic Lobe dataset."""

    OPTIC_REGIONS = {"ME", "LO", "LOP", "AME", "LA"}

    def get_central_brain_rois(self, all_rois: List[str]) -> List[str]:
        """
        For optic-lobe dataset, central brain is everything that is NOT:
        - ME, LO, LOP, AME, LA
        - Layer patterns: [ME|LO|LOP]_[RL]_layer.*
        - Column patterns: [ME|LO|LOP]_[RL]_col.*
        """
        excluded_rois = set()

        # Add direct optic regions
        for roi in all_rois:
            # Check for basic optic regions with or without side indicators
            roi_base = (
                roi.replace("(L)", "")
                .replace("(R)", "")
                .replace("_L", "")
                .replace("_R", "")
            )
            if roi_base in self.OPTIC_REGIONS:
                excluded_rois.add(roi)

        # Add layer patterns
        layer_pattern = r"^(ME|LO|LOP)_[RL]_layer.*$"
        for roi in all_rois:
            if re.match(layer_pattern, roi):
                excluded_rois.add(roi)

        # Add column patterns
        column_pattern = r"^(ME|LO|LOP)_[RL]_col.*$"
        for roi in all_rois:
            if re.match(column_pattern, roi):
                excluded_rois.add(roi)

        # Handle both parenthetical and underscore OL patterns
        ol_patterns = [r"^OL\([RL]\)$", r"^OL_[RL]$"]
        for roi in all_rois:
            if any(re.match(pattern, roi) for pattern in ol_patterns):
                excluded_rois.add(roi)

        # Central brain is everything else
        central_brain_rois = [roi for roi in all_rois if roi not in excluded_rois]
        return central_brain_rois

    def get_primary_rois(self, all_rois: List[str]) -> List[str]:
        """Get primary ROIs for optic lobe dataset."""
        excluded_rois = {
            "OL(R)",
            "OL(L)",
            "OL_R",
            "OL_L",
        }  # Exclude these from optic-lobe ROI table
        primary_rois = []

        # Add main optic regions with side indicators
        for roi in all_rois:
            if roi in excluded_rois:
                continue
            if any(f"{region}(" in roi for region in self.OPTIC_REGIONS):
                primary_rois.append(roi)

        # Add central brain regions (simplified)
        central_rois = self.get_central_brain_rois(all_rois)
        # Take only major central brain ROIs (avoid sub-regions)
        for roi in central_rois:
            if roi in excluded_rois:
                continue
            if "(" in roi and len(roi) <= 8:  # Simple heuristic for main ROIs
                primary_rois.append(roi)

        return primary_rois

    def categorize_rois(self, all_rois: List[str]) -> Dict[str, List[str]]:
        """Categorize ROIs for optic lobe dataset."""
        categories = {
            "central_brain": self.get_central_brain_rois(all_rois),
            "optic_regions": [],
            "layers": self.filter_rois_by_type(all_rois, "layers"),
            "columns": self.filter_rois_by_type(all_rois, "columns"),
            "other": [],
        }

        # Identify optic regions
        for roi in all_rois:
            roi_base = (
                roi.replace("(L)", "")
                .replace("(R)", "")
                .replace("_L", "")
                .replace("_R", "")
            )
            if roi_base in self.OPTIC_REGIONS:
                categories["optic_regions"].append(roi)

        # Classify remaining ROIs
        categorized = set(
            categories["central_brain"]
            + categories["optic_regions"]
            + categories["layers"]
            + categories["columns"]
        )

        for roi in all_rois:
            if roi not in categorized:
                categories["other"].append(roi)

        return categories

    def filter_rois_by_type(self, all_rois: List[str], roi_type: str) -> List[str]:
        """Filter ROIs by type for optic lobe."""
        if roi_type == "central_brain":
            return self.get_central_brain_rois(all_rois)
        elif roi_type == "layers":
            layer_pattern = r"^(ME|LO|LOP)_[RL]_layer.*$"
            return [roi for roi in all_rois if re.match(layer_pattern, roi)]
        elif roi_type == "columns":
            column_pattern = r"^(ME|LO|LOP)_[RL]_col.*$"
            return [roi for roi in all_rois if re.match(column_pattern, roi)]
        elif roi_type == "optic_regions":
            optic_rois = []
            for roi in all_rois:
                roi_base = (
                    roi.replace("(L)", "")
                    .replace("(R)", "")
                    .replace("_L", "")
                    .replace("_R", "")
                )
                if roi_base in self.OPTIC_REGIONS:
                    optic_rois.append(roi)
            return optic_rois
        else:
            return []


class HemibrainRoiQueryStrategy(RoiQueryStrategy):
    """ROI query strategy for Hemibrain dataset."""

    def get_central_brain_rois(self, all_rois: List[str]) -> List[str]:
        """Hemibrain typically has explicit central brain regions."""
        central_patterns = [
            r".*[Cc]entral[Bb]rain.*",
            r"^[A-Z]{2,4}\([LR]\)$",  # Major ROIs like FB(R), PB(L)
        ]
        central_rois = []
        for roi in all_rois:
            if any(re.match(pattern, roi) for pattern in central_patterns):
                central_rois.append(roi)
        return central_rois

    def get_primary_rois(self, all_rois: List[str]) -> List[str]:
        """Get primary ROIs for Hemibrain."""
        return self.get_central_brain_rois(all_rois)

    def categorize_rois(self, all_rois: List[str]) -> Dict[str, List[str]]:
        """Categorize ROIs for Hemibrain dataset."""
        categories = {
            "central_brain": self.get_central_brain_rois(all_rois),
            "visual_system": [],
            "other": [],
        }

        # Simple visual system detection
        visual_patterns = [r".*[Oo]ptic.*", r".*ME.*", r".*LO.*"]
        for roi in all_rois:
            if any(re.match(pattern, roi) for pattern in visual_patterns):
                categories["visual_system"].append(roi)

        # Classify remaining
        categorized = set(categories["central_brain"] + categories["visual_system"])
        for roi in all_rois:
            if roi not in categorized:
                categories["other"].append(roi)

        return categories

    def filter_rois_by_type(self, all_rois: List[str], roi_type: str) -> List[str]:
        """Filter ROIs by type for Hemibrain."""
        if roi_type == "central_brain":
            return self.get_central_brain_rois(all_rois)
        elif roi_type == "visual":
            categories = self.categorize_rois(all_rois)
            return categories.get("visual_system", [])
        else:
            return []


class DatasetAdapter(ABC):
    """Base class for dataset-specific adapters."""

    def __init__(
        self,
        dataset_info: Optional[DatasetInfo] = None,
        roi_strategy: Optional[RoiQueryStrategy] = None,
    ):
        self.dataset_info = dataset_info
        self.roi_strategy = roi_strategy

    @abstractmethod
    def extract_soma_side(self, neurons_df: pd.DataFrame) -> pd.DataFrame:
        """Extract soma side information from the dataset."""
        pass

    @abstractmethod
    def normalize_columns(self, neurons_df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names to standard format."""
        pass

    @abstractmethod
    def get_synapse_counts(self, neurons_df: pd.DataFrame) -> Tuple[int, int]:
        """Get total pre and post synapse counts."""
        pass

    def filter_by_soma_side(self, neurons_df: pd.DataFrame, soma_side) -> pd.DataFrame:
        """Filter neurons by soma side."""
        # Handle both string and SomaSide enum inputs

        # Convert to string value for processing
        if hasattr(soma_side, "value"):
            # It's a SomaSide enum
            soma_side_str = soma_side.value
        else:
            # It's already a string
            soma_side_str = str(soma_side)

        if soma_side_str in ["combined", "all"]:
            return neurons_df

        # Ensure soma side is extracted
        neurons_df = self.extract_soma_side(neurons_df)

        if "somaSide" not in neurons_df.columns:
            dataset_name = self.dataset_info.name if self.dataset_info else "unknown"
            raise ValueError(f"Cannot filter by soma side for dataset {dataset_name}")

        # Handle 'L'/'R' and 'left'/'right' formats
        side_filter = None
        if soma_side_str.lower() in ["left", "l"]:
            side_filter = "L"
        elif soma_side_str.lower() in ["right", "r"]:
            side_filter = "R"
        elif soma_side_str.lower() in ["middle", "m"]:
            side_filter = "M"
        else:
            raise ValueError(
                f"Invalid soma side: {soma_side_str}. Use 'L', 'R', 'M', 'left', 'right', 'middle', 'combined', or 'all'"
            )

        return neurons_df[neurons_df["somaSide"] == side_filter]

    def get_available_columns(self, neurons_df: pd.DataFrame) -> List[str]:
        """Get list of available columns in the dataset."""
        return list(neurons_df.columns)

    def query_central_brain_rois(self, all_rois: List[str]) -> List[str]:
        """Query ROIs that constitute the central brain for this dataset."""
        if self.roi_strategy:
            return self.roi_strategy.get_central_brain_rois(all_rois)
        return []

    def query_primary_rois(self, all_rois: List[str]) -> List[str]:
        """Query primary/main ROIs for this dataset."""
        if self.roi_strategy:
            return self.roi_strategy.get_primary_rois(all_rois)
        return []

    def categorize_rois(self, all_rois: List[str]) -> Dict[str, List[str]]:
        """Categorize ROIs into functional groups."""
        if self.roi_strategy:
            return self.roi_strategy.categorize_rois(all_rois)
        return {"other": all_rois}

    def filter_rois_by_type(self, all_rois: List[str], roi_type: str) -> List[str]:
        """Filter ROIs by specified type."""
        if self.roi_strategy:
            return self.roi_strategy.filter_rois_by_type(all_rois, roi_type)
        return []


class CNSAdapter(DatasetAdapter):
    """Adapter for CNS dataset."""

    def __init__(self):
        dataset_info = DatasetInfo(
            name="cns",
            soma_side_column="somaSide",
            pre_synapse_column="pre",
            post_synapse_column="post",
            upstream_column="upstream",
            downstream_column="downstream",
            roi_columns=["inputRois", "outputRois"],
        )
        roi_strategy = CNSRoiQueryStrategy()
        super().__init__(dataset_info, roi_strategy)

    def extract_soma_side(self, neurons_df: pd.DataFrame) -> pd.DataFrame:
        """CNS prioritizes rootSide over somaSide."""
        neurons_df = neurons_df.copy()

        # Check if rootSide exists and use it as primary source
        if "rootSide" in neurons_df.columns:
            # Use rootSide as primary, fall back to somaSide for null values
            if "somaSide" in neurons_df.columns:
                # Combine rootSide and somaSide with rootSide taking priority
                neurons_df["somaSide"] = (
                    neurons_df["rootSide"].fillna(neurons_df["somaSide"]).fillna("U")
                )
            else:
                # Only rootSide available
                neurons_df["somaSide"] = neurons_df["rootSide"].fillna("U")
            return neurons_df
        elif "somaSide" in neurons_df.columns:
            # Fall back to original somaSide if rootSide not available
            neurons_df["somaSide"] = neurons_df["somaSide"].fillna("U")
            return neurons_df
        else:
            # If neither column exists, create it as unknown
            neurons_df["somaSide"] = "U"  # Unknown
            return neurons_df

    def normalize_columns(self, neurons_df: pd.DataFrame) -> pd.DataFrame:
        """CNS columns are already in standard format."""
        return neurons_df

    def get_synapse_counts(self, neurons_df: pd.DataFrame) -> Tuple[int, int]:
        """Get synapse counts from CNS dataset."""
        pre_total = (
            neurons_df[self.dataset_info.pre_synapse_column].sum()
            if self.dataset_info.pre_synapse_column in neurons_df.columns
            else 0
        )
        post_total = (
            neurons_df[self.dataset_info.post_synapse_column].sum()
            if self.dataset_info.post_synapse_column in neurons_df.columns
            else 0
        )
        return int(pre_total), int(post_total)

    def get_connection_counts(self, neurons_df: pd.DataFrame) -> Tuple[int, int]:
        """Get connection counts from CNS dataset."""
        up_total = (
            neurons_df[self.dataset_info.upstream_column].sum()
            if self.dataset_info.upstream_column in neurons_df.columns
            else 0
        )
        down_total = (
            neurons_df[self.dataset_info.downstream_column].sum()
            if self.dataset_info.downstream_column in neurons_df.columns
            else 0
        )
        return int(up_total), int(down_total)

class HemibrainAdapter(DatasetAdapter):
    """Adapter for Hemibrain dataset."""

    def __init__(self):
        dataset_info = DatasetInfo(
            name="hemibrain",
            soma_side_column="somaSide",
            pre_synapse_column="pre",
            post_synapse_column="post",
            upstream_column="upstream",
            downstream_column="downstream",
            roi_columns=["inputRois", "outputRois"],
        )
        roi_strategy = HemibrainRoiQueryStrategy()
        super().__init__(dataset_info, roi_strategy)

    def extract_soma_side(self, neurons_df: pd.DataFrame) -> pd.DataFrame:
        """Hemibrain prioritizes rootSide over somaSide."""
        neurons_df = neurons_df.copy()

        # Check if rootSide exists and use it as primary source
        if "rootSide" in neurons_df.columns:
            # Use rootSide as primary, fall back to somaSide for null values
            if "somaSide" in neurons_df.columns:
                # Combine rootSide and somaSide with rootSide taking priority
                neurons_df["somaSide"] = (
                    neurons_df["rootSide"].fillna(neurons_df["somaSide"]).fillna("U")
                )
            else:
                # Only rootSide available
                neurons_df["somaSide"] = neurons_df["rootSide"].fillna("U")
            return neurons_df
        elif "somaSide" in neurons_df.columns:
            # Fall back to original somaSide if rootSide not available
            return neurons_df
        else:
            # If missing, try to extract from instance name
            if "instance" in neurons_df.columns:
                # Extract from instance names like "neuronType_R" or "neuronType_L"
                neurons_df["somaSide"] = neurons_df["instance"].str.extract(
                    r"_([LR])$"
                )[0]
                neurons_df["somaSide"] = neurons_df["somaSide"].fillna("U")
            else:
                neurons_df["somaSide"] = "U"
            return neurons_df

    def normalize_columns(self, neurons_df: pd.DataFrame) -> pd.DataFrame:
        """Normalize Hemibrain columns."""
        return neurons_df

    def get_synapse_counts(self, neurons_df: pd.DataFrame) -> Tuple[int, int]:
        """Get synapse counts from Hemibrain dataset."""
        pre_total = (
            neurons_df[self.dataset_info.pre_synapse_column].sum()
            if self.dataset_info.pre_synapse_column in neurons_df.columns
            else 0
        )
        post_total = (
            neurons_df[self.dataset_info.post_synapse_column].sum()
            if self.dataset_info.post_synapse_column in neurons_df.columns
            else 0
        )
        return int(pre_total), int(post_total)

    
    def get_connection_counts(self, neurons_df: pd.DataFrame) -> Tuple[int, int]:
        """Get connection counts from Hemibrain dataset."""
        up_total = (
            neurons_df[self.dataset_info.upstream_column].sum()
            if self.dataset_info.upstream_column in neurons_df.columns
            else 0
        )
        down_total = (
            neurons_df[self.dataset_info.downstream_column].sum()
            if self.dataset_info.downstream_column in neurons_df.columns
            else 0
        )
        return int(up_total), int(down_total)

class OpticLobeAdapter(DatasetAdapter):
    """Adapter for Optic Lobe dataset."""

    def __init__(self):
        dataset_info = DatasetInfo(
            name="optic-lobe",
            soma_side_extraction=r"(?:_|-|\()([LRMlrm])(?:_|\)|$|[^a-zA-Z])",  # Extract L, R, or M from instance names with flexible delimiters
            pre_synapse_column="pre",
            post_synapse_column="post",
            upstream_column="upstream",
            downstream_column="downstream",
            roi_columns=["inputRois", "outputRois"],
        )
        roi_strategy = OpticLobeRoiQueryStrategy()
        super().__init__(dataset_info, roi_strategy)

    def extract_soma_side(self, neurons_df: pd.DataFrame) -> pd.DataFrame:
        """Extract soma side prioritizing rootSide over somaSide, with instance name fallback."""
        neurons_df = neurons_df.copy()

        # Check if rootSide exists and use it as primary source
        if "rootSide" in neurons_df.columns:
            # Use rootSide as primary, fall back to somaSide for null values
            if "somaSide" in neurons_df.columns:
                # Combine rootSide and somaSide with rootSide taking priority
                neurons_df["somaSide"] = (
                    neurons_df["rootSide"].fillna(neurons_df["somaSide"]).fillna("U")
                )
            else:
                # Only rootSide available
                neurons_df["somaSide"] = neurons_df["rootSide"].fillna("U")
            return neurons_df
        elif "somaSide" in neurons_df.columns:
            # Fall back to original somaSide if rootSide not available
            return neurons_df
        elif (
            "instance" in neurons_df.columns and self.dataset_info.soma_side_extraction
        ):
            # Extract soma side from instance names
            # Patterns like: "LC4_L", "LPLC2_R_001", "T4_L_medulla", "VES022(L)", "VES022-R"
            pattern = self.dataset_info.soma_side_extraction
            extracted = neurons_df["instance"].str.extract(pattern, expand=False)
            # Convert to uppercase for consistency
            neurons_df["somaSide"] = extracted.str.upper().fillna(
                "U"
            )  # Unknown if not found
        else:
            neurons_df["somaSide"] = "U"

        return neurons_df

    def normalize_columns(self, neurons_df: pd.DataFrame) -> pd.DataFrame:
        """Normalize Optic Lobe columns."""
        # Optic lobe might have different column names
        column_mapping = {
            # Add any column name mappings specific to optic lobe
            # 'old_name': 'new_name'
        }

        if column_mapping:
            neurons_df = neurons_df.rename(columns=column_mapping)

        return neurons_df

    def get_synapse_counts(self, neurons_df: pd.DataFrame) -> Tuple[int, int]:
        """Get synapse counts from Optic Lobe dataset."""
        pre_total = (
            neurons_df[self.dataset_info.pre_synapse_column].sum()
            if self.dataset_info.pre_synapse_column in neurons_df.columns
            else 0
        )
        post_total = (
            neurons_df[self.dataset_info.post_synapse_column].sum()
            if self.dataset_info.post_synapse_column in neurons_df.columns
            else 0
        )
        return int(pre_total), int(post_total)
    
    def get_connection_counts(self, neurons_df: pd.DataFrame) -> Tuple[int, int]:
        """Get connection counts from Optic Lobe dataset."""
        up_total = (
            neurons_df[self.dataset_info.upstream_column].sum()
            if self.dataset_info.upstream_column in neurons_df.columns
            else 0
        )
        down_total = (
            neurons_df[self.dataset_info.downstream_column].sum()
            if self.dataset_info.downstream_column in neurons_df.columns
            else 0
        )
        return int(up_total), int(down_total)


class FafbAdapter(DatasetAdapter):
    """Adapter for FlyWire FAFB dataset."""

    def __init__(self):
        dataset_info = DatasetInfo(
            name="flywire-fafb",
            soma_side_extraction=r"(?:_|-|\()([LRMlrm])(?:_|\)|$|[^a-zA-Z])",  # Extract L, R, or M from instance names with flexible delimiters
            pre_synapse_column="pre",
            post_synapse_column="post",
            upstream_column="upstream",
            downstream_column="downstream",
            roi_columns=["inputRois", "outputRois"],
        )
        roi_strategy = (
            OpticLobeRoiQueryStrategy()
        )  # FAFB is visual system data, use optic lobe ROI strategy
        super().__init__(dataset_info, roi_strategy)

    def extract_soma_side(self, neurons_df: pd.DataFrame) -> pd.DataFrame:
        """Extract soma side prioritizing rootSide over somaSide, with FAFB-specific handling."""
        neurons_df = neurons_df.copy()

        # Build the cascade of fallback values
        result_series = None

        # First priority: rootSide
        if "rootSide" in neurons_df.columns:
            result_series = neurons_df["rootSide"].copy()

        # Second priority: somaSide (fill nulls from rootSide)
        if "somaSide" in neurons_df.columns:
            if result_series is not None:
                result_series = result_series.fillna(neurons_df["somaSide"])
            else:
                result_series = neurons_df["somaSide"].copy()

        # Third priority: FAFB-specific 'side' property (fill remaining nulls)
        if "side" in neurons_df.columns:
            side_mapping = {
                "LEFT": "L",
                "RIGHT": "R",
                "CENTER": "M",
                "MIDDLE": "M",
                "left": "L",
                "right": "R",
                "center": "M",
                "middle": "M",
                "L": "L",
                "R": "R",
                "C": "M",
                "M": "M",
            }
            mapped_side = neurons_df["side"].map(side_mapping)
            if result_series is not None:
                result_series = result_series.fillna(mapped_side)
            else:
                result_series = mapped_side.copy()

        # Fourth priority: instance name extraction (fill remaining nulls)
        if (
            "instance" in neurons_df.columns
            and self.dataset_info.soma_side_extraction
            and result_series is not None
            and result_series.isna().any()
        ):
            pattern = self.dataset_info.soma_side_extraction
            extracted = neurons_df["instance"].str.extract(pattern, expand=False)
            extracted_upper = extracted.str.upper()
            result_series = result_series.fillna(extracted_upper)

        # Final fallback: set any remaining nulls to 'U' (Unknown)
        if result_series is not None:
            neurons_df["somaSide"] = result_series.fillna("U")
        else:
            neurons_df["somaSide"] = "U"

        return neurons_df

    def normalize_neurotransmitter_data(self, neurons_df: pd.DataFrame) -> pd.DataFrame:
        """Normalize FAFB neurotransmitter data to standard format."""
        neurons_df = neurons_df.copy()

        # FAFB uses predictedNt and predictedNtProb instead of consensusNt
        if (
            "predictedNt" in neurons_df.columns
            and "consensusNt" not in neurons_df.columns
        ):
            # Map predictedNt to consensusNt for compatibility
            neurons_df["consensusNt"] = neurons_df["predictedNt"]

        if (
            "predictedNtProb" in neurons_df.columns
            and "celltypePredictedNtConfidence" not in neurons_df.columns
        ):
            # Map predictedNtProb to celltypePredictedNtConfidence for compatibility
            neurons_df["celltypePredictedNtConfidence"] = neurons_df["predictedNtProb"]

        # Also map to celltypePredictedNt for consistency
        if (
            "predictedNt" in neurons_df.columns
            and "celltypePredictedNt" not in neurons_df.columns
        ):
            neurons_df["celltypePredictedNt"] = neurons_df["predictedNt"]

        return neurons_df

    def normalize_columns(self, neurons_df: pd.DataFrame) -> pd.DataFrame:
        """Normalize FAFB columns."""
        # First apply neurotransmitter normalization
        neurons_df = self.normalize_neurotransmitter_data(neurons_df)

        # FAFB might have different column names specific to FlyWire data
        column_mapping = {
            # Add any column name mappings specific to FAFB/FlyWire
            # 'old_name': 'new_name'
        }

        if column_mapping:
            neurons_df = neurons_df.rename(columns=column_mapping)

        return neurons_df

    def get_synapse_counts(self, neurons_df: pd.DataFrame) -> Tuple[int, int]:
        """Get synapse counts from FAFB dataset."""
        pre_total = (
            neurons_df[self.dataset_info.pre_synapse_column].sum()
            if self.dataset_info.pre_synapse_column in neurons_df.columns
            else 0
        )
        post_total = (
            neurons_df[self.dataset_info.post_synapse_column].sum()
            if self.dataset_info.post_synapse_column in neurons_df.columns
            else 0
        )
        return int(pre_total), int(post_total)
    
    def get_connection_counts(self, neurons_df: pd.DataFrame) -> Tuple[int, int]:
        """Get connection counts from FAFB dataset."""
        up_total = (
            neurons_df[self.dataset_info.upstream_column].sum()
            if self.dataset_info.upstream_column in neurons_df.columns
            else 0
        )
        down_total = (
            neurons_df[self.dataset_info.downstream_column].sum()
            if self.dataset_info.downstream_column in neurons_df.columns
            else 0
        )
        return int(up_total), int(down_total)


class DatasetAdapterFactory:
    """Factory for creating dataset adapters."""

    _adapters: Dict[str, Type[DatasetAdapter]] = {
        "cns": CNSAdapter,
        "hemibrain": HemibrainAdapter,
        "optic-lobe": OpticLobeAdapter,
        "flywire-fafb": FafbAdapter,
    }

    # Dataset aliases - map alternative names to canonical names
    _aliases: Dict[str, str] = {
        "male-cns": "cns",
    }

    @classmethod
    def create_adapter(cls, dataset_name: str) -> DatasetAdapter:
        """Create appropriate adapter for the dataset."""
        # Handle versioned dataset names
        base_name = dataset_name.split(":")[0] if ":" in dataset_name else dataset_name

        # Resolve aliases
        resolved_name = cls._aliases.get(base_name, base_name)

        if dataset_name in cls._adapters:
            return cls._adapters[dataset_name]()
        elif base_name in cls._adapters:
            return cls._adapters[base_name]()
        elif resolved_name in cls._adapters:
            return cls._adapters[resolved_name]()
        else:
            # Default to CNS adapter for unknown datasets
            print(
                f"Warning: Unknown dataset '{dataset_name}', using CNS adapter as default"
            )
            return CNSAdapter()

    @classmethod
    def register_adapter(cls, dataset_name: str, adapter_class: type):
        """Register a new adapter for a dataset."""
        cls._adapters[dataset_name] = adapter_class

    @classmethod
    def get_supported_datasets(cls) -> List[str]:
        """Get list of supported datasets."""
        return list(cls._adapters.keys())


def get_dataset_adapter(dataset_name: str) -> DatasetAdapter:
    """Convenience function to get dataset adapter."""
    return DatasetAdapterFactory.create_adapter(dataset_name)
