# =============================================================================
# SEEGPlanner — Extensión para 3D Slicer para planificación de electrodos SEEG
# Copyright (c) 2026 Alejandra Viñegla Sánchez
# Tutores: Víctor Manuel Smith Fernández, David Bueno Vallejo (Universidad de Málaga)
# Licensed under the MIT License.
# Built with dbv-specs-ops · https://github.com/davidbuenov/dbv-specs-ops
# =============================================================================

from __future__ import annotations

import logging
import os
import sys
from typing import Any, Dict, List, Tuple

import numpy as np

try:
    import ctk
    import qt
    import slicer
    import vtk
    from slicer.ScriptedLoadableModule import (
        ScriptedLoadableModule,
        ScriptedLoadableModuleLogic,
        ScriptedLoadableModuleTest,
        ScriptedLoadableModuleWidget,
    )
except ImportError:
    # Soporte para ejecución e inspección estática fuera de 3D Slicer
    ctk = None
    qt = None
    slicer = None
    vtk = None
    ScriptedLoadableModule = object
    ScriptedLoadableModuleWidget = object
    ScriptedLoadableModuleLogic = object
    ScriptedLoadableModuleTest = object

# Inclusión dinámica del submódulo Logic
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
if MODULE_DIR not in sys.path:
    sys.path.insert(0, MODULE_DIR)

try:
    from Logic.eeg_1020_calculator import (
        CanonicalLandmarks,
        calculate_1020_points,
        project_points_to_surface_mesh,
    )
    from Logic.igtlink_exporter import (
        export_trajectories_to_csv_file,
        export_trajectories_to_json_file,
        export_trajectories_to_slicer_markups_json,
        transmit_openigtlink_trajectories,
    )
    from Logic.result import Err, Ok, Result
    from Logic.skull_surface_extractor import (
        SurfaceExtractionParams,
        extract_head_surface_polydata,
        get_surface_normal_at_point,
    )
    from Logic.target_manager import (
        TargetStructure,
        VolumeMetadata,
        compute_segment_target,
        validate_volume_metadata,
    )
    from Logic.trajectory_planner import (
        ContactPoint,
        ElectrodeConfig,
        TrajectoryConflict,
        TrajectoryMetrics,
        calculate_electrode_contacts,
        calculate_trajectory,
        check_trajectory_conflicts,
        compute_segment_to_segment_distance,
        generate_electrode_tube_polydata,
        point_to_segment_distance,
    )
except ImportError:
    from .Logic.eeg_1020_calculator import (
        CanonicalLandmarks,
        calculate_1020_points,
        project_points_to_surface_mesh,
    )
    from .Logic.igtlink_exporter import export_trajectories_to_json_file
    from .Logic.result import Err, Ok, Result
    from .Logic.skull_surface_extractor import (
        SurfaceExtractionParams,
        extract_head_surface_polydata,
        get_surface_normal_at_point,
    )
    from .Logic.target_manager import (
        TargetStructure,
        VolumeMetadata,
        compute_segment_target,
        validate_volume_metadata,
    )
    from .Logic.trajectory_planner import (
        ContactPoint,
        ElectrodeConfig,
        TrajectoryConflict,
        TrajectoryMetrics,
        calculate_electrode_contacts,
        calculate_trajectory,
        check_trajectory_conflicts,
        compute_segment_to_segment_distance,
        generate_electrode_tube_polydata,
        point_to_segment_distance,
    )


class SEEGPlanner(ScriptedLoadableModule):
    """Metadatos y configuración del módulo para el Administrador de Extensiones de 3D Slicer."""

    def __init__(self, parent: Any) -> None:
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "SEEG Planner"
        self.parent.categories = ["Neurosurgery"]
        self.parent.dependencies = []
        self.parent.contributors = [
            "Alejandra Viñegla Sánchez (Universidad de Málaga)",
            "Víctor Manuel Smith Fernández (Tutor)",
            "David Bueno Vallejo (Cotutor)",
        ]
        self.parent.helpText = (
            "Herramienta integral para la planificación quirúrgica de electrodos de "
            "estéreo-electroencefalografía (SEEG). Integra mapeo anatómico EEG 10-20, "
            "localización volumétrica de dianas cerebrales, verificación biomecánica y OpenIGTLink."
        )
        self.parent.acknowledgementText = (
            "Desarrollado como Trabajo de Fin de Grado en Ingeniería de la Salud en la "
            "Universidad de Málaga, siguiendo el framework Spec-Driven Development dbv-specs-ops."
        )


class SEEGPlannerWidget(ScriptedLoadableModuleWidget):
    """Interfaz gráfica de usuario nativa de 3D Slicer con flujo de trabajo clínico por secciones."""

    def __init__(self, parent: Any = None) -> None:
        ScriptedLoadableModuleWidget.__init__(self, parent)
        self.logic = SEEGPlannerLogic()
        self.planned_trajectories: List[TrajectoryMetrics] = []
        self.extracted_targets: List[TargetStructure] = []
        self._isUpdatingUI: bool = False

    def setup(self) -> None:
        """Inicializa la interfaz gráfica y conecta los controles Qt con la lógica."""
        ScriptedLoadableModuleWidget.setup(self)

        # Contenedor principal con diseño vertical
        parametersLayout = qt.QVBoxLayout(self.layout)

        # ---------------------------------------------------------------------
        # 1. Sección: Volumen Neuroanatómico (MRI)
        # ---------------------------------------------------------------------
        self.volumeCollapsibleButton = ctk.ctkCollapsibleButton()
        self.volumeCollapsibleButton.text = "1. Resonancia Magnética (MRI)"
        parametersLayout.addWidget(self.volumeCollapsibleButton)

        volumeLayout = qt.QFormLayout(self.volumeCollapsibleButton)
        self.volumeSelector = slicer.qMRMLNodeComboBox()
        self.volumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.volumeSelector.selectNodeUponCreation = True
        self.volumeSelector.addEnabled = True
        self.volumeSelector.removeEnabled = False
        self.volumeSelector.noneEnabled = True
        self.volumeSelector.showHidden = False
        self.volumeSelector.showChildNodeTypes = False
        self.volumeSelector.setMRMLScene(slicer.mrmlScene)
        self.volumeSelector.setToolTip("Seleccione el volumen cerebral MRI de referencia del paciente.")
        volumeLayout.addRow("Volumen MRI:", self.volumeSelector)

        self.lblVolumeInfo = qt.QLabel("Estado: Seleccione un volumen MRI para inspección técnica.")
        self.lblVolumeInfo.setWordWrap(True)
        volumeLayout.addRow("Control Calidad:", self.lblVolumeInfo)

        self.btnCenterViews = qt.QPushButton("Recentrar Vistas Ortogonales (Axial, Sagital, Coronal)")
        volumeLayout.addRow(self.btnCenterViews)

        # ---------------------------------------------------------------------
        # 2. Sección: Referencias Anatómicas y Mapeo EEG 10-20
        # ---------------------------------------------------------------------
        self.eegCollapsibleButton = ctk.ctkCollapsibleButton()
        self.eegCollapsibleButton.text = "2. Sistema EEG 10-20 & Referencias"
        parametersLayout.addWidget(self.eegCollapsibleButton)

        eegLayout = qt.QFormLayout(self.eegCollapsibleButton)

        self.refFiducialsSelector = slicer.qMRMLNodeComboBox()
        self.refFiducialsSelector.nodeTypes = ["vtkMRMLMarkupsFiducialNode"]
        self.refFiducialsSelector.selectNodeUponCreation = True
        self.refFiducialsSelector.addEnabled = True
        self.refFiducialsSelector.renameEnabled = True
        self.refFiducialsSelector.baseName = "AnatomicalLandmarks"
        self.refFiducialsSelector.setMRMLScene(slicer.mrmlScene)
        self.refFiducialsSelector.setToolTip("Nodo con los 4 fiduciales básicos: Nasion, Inion, LPA y RPA.")
        eegLayout.addRow("Fiduciales Base (Nz, Iz, LPA, RPA):", self.refFiducialsSelector)

        self.btnCreateTemplateLandmarks = qt.QPushButton("Crear Plantilla de 4 Fiduciales")
        self.btnCreateTemplateLandmarks.toolTip = (
            "Crea un nodo de marcas inicial con etiquetas Nasion, Inion, LPA y RPA listas para ajustar."
        )
        eegLayout.addRow(self.btnCreateTemplateLandmarks)

        # Asistente de fijación interactiva de referencias
        landmarksBtnLayout = qt.QHBoxLayout()
        self.btnPlaceNz = qt.QPushButton("Fijar Nz")
        self.btnPlaceIz = qt.QPushButton("Fijar Iz")
        self.btnPlaceLPA = qt.QPushButton("Fijar LPA")
        self.btnPlaceRPA = qt.QPushButton("Fijar RPA")
        landmarksBtnLayout.addWidget(self.btnPlaceNz)
        landmarksBtnLayout.addWidget(self.btnPlaceIz)
        landmarksBtnLayout.addWidget(self.btnPlaceLPA)
        landmarksBtnLayout.addWidget(self.btnPlaceRPA)
        eegLayout.addRow("Asistente Puntos:", landmarksBtnLayout)

        # Superficie 3D de la cabeza
        self.headSurfaceSelector = slicer.qMRMLNodeComboBox()
        self.headSurfaceSelector.nodeTypes = ["vtkMRMLModelNode"]
        self.headSurfaceSelector.selectNodeUponCreation = False
        self.headSurfaceSelector.addEnabled = False
        self.headSurfaceSelector.removeEnabled = False
        self.headSurfaceSelector.noneEnabled = True
        self.headSurfaceSelector.showHidden = False
        self.headSurfaceSelector.showChildNodeTypes = False
        self.headSurfaceSelector.setMRMLScene(slicer.mrmlScene)
        self.headSurfaceSelector.setToolTip("Modelo 3D de la superficie cutánea o craneal del paciente.")
        eegLayout.addRow("Superficie Cabeza 3D:", self.headSurfaceSelector)

        self.btnGenerateHeadSurface = qt.QPushButton("Generar Superficie 3D de la Cabeza (Marching Cubes)")
        self.btnGenerateHeadSurface.toolTip = "Extrae automáticamente la malla cutánea del paciente a partir del volumen MRI."
        eegLayout.addRow(self.btnGenerateHeadSurface)

        self.chkProjectOnSurface = qt.QCheckBox("Proyectar electrodos 10-20 sobre superficie cutánea")
        self.chkProjectOnSurface.setChecked(True)
        eegLayout.addRow(self.chkProjectOnSurface)

        self.btnCompute1020 = qt.QPushButton("Calcular y Proyectar Rejilla EEG 10-20")
        self.btnCompute1020.setStyleSheet("font-weight: bold; background-color: #2b5b84; color: white;")
        eegLayout.addRow(self.btnCompute1020)

        # ---------------------------------------------------------------------
        # 3. Sección: Dianas Cerebrales & Parámetros de Electrodo
        # ---------------------------------------------------------------------
        self.trajCollapsibleButton = ctk.ctkCollapsibleButton()
        self.trajCollapsibleButton.text = "3. Dianas Cerebrales & Parámetros de Electrodo"
        parametersLayout.addWidget(self.trajCollapsibleButton)

        trajLayout = qt.QFormLayout(self.trajCollapsibleButton)

        # Selector de Segmentación para extracción de dianas
        self.segmentationSelector = slicer.qMRMLNodeComboBox()
        self.segmentationSelector.nodeTypes = ["vtkMRMLSegmentationNode"]
        self.segmentationSelector.selectNodeUponCreation = False
        self.segmentationSelector.addEnabled = False
        self.segmentationSelector.removeEnabled = False
        self.segmentationSelector.noneEnabled = True
        self.segmentationSelector.showHidden = False
        self.segmentationSelector.showChildNodeTypes = False
        self.segmentationSelector.setMRMLScene(slicer.mrmlScene)
        self.segmentationSelector.setToolTip("Seleccione la segmentación con las estructuras cerebrales (hipocampo, amígdala...).")
        trajLayout.addRow("Segmentación Cerebral:", self.segmentationSelector)

        self.btnExtractTargets = qt.QPushButton("Extraer Centroides de Dianas Anatómicas")
        self.btnExtractTargets.setStyleSheet("font-weight: bold; background-color: #5c3b88; color: white;")
        trajLayout.addRow(self.btnExtractTargets)

        self.targetsTableWidget = qt.QTableWidget()
        self.targetsTableWidget.setColumnCount(4)
        self.targetsTableWidget.setHorizontalHeaderLabels(["Estructura", "Vol (mm³)", "Centroide RAS", "En Masa"])
        self.targetsTableWidget.horizontalHeader().setStretchLastSection(True)
        self.targetsTableWidget.setMaximumHeight(130)
        trajLayout.addRow("Dianas Detectadas:", self.targetsTableWidget)

        self.entryPointSelector = slicer.qMRMLNodeComboBox()
        self.entryPointSelector.nodeTypes = ["vtkMRMLMarkupsFiducialNode"]
        self.entryPointSelector.setMRMLScene(slicer.mrmlScene)
        self.entryPointSelector.setToolTip("Fiducial o punto de entrada craneal (ej. electrodo 10-20).")
        trajLayout.addRow("Punto de Entrada (Cráneo):", self.entryPointSelector)

        self.targetPointSelector = slicer.qMRMLNodeComboBox()
        self.targetPointSelector.nodeTypes = ["vtkMRMLMarkupsFiducialNode"]
        self.targetPointSelector.setMRMLScene(slicer.mrmlScene)
        self.targetPointSelector.baseName = "SEEG_Targets"
        self.targetPointSelector.setToolTip("Fiducial de la diana cerebral (hipocampo, amígdala, etc.).")
        trajLayout.addRow("Punto Diana (Cerebro):", self.targetPointSelector)

        # Configuración de electrodo y perno guía
        electrodeParamsLayout = qt.QHBoxLayout()
        self.spinDiameter = qt.QDoubleSpinBox()
        self.spinDiameter.setRange(0.4, 2.5)
        self.spinDiameter.setValue(0.8)
        self.spinDiameter.setSingleStep(0.1)
        self.spinDiameter.setSuffix(" mm")
        self.spinDiameter.setToolTip("Diámetro nominal del electrodo SEEG (calibre clínico estándar: 0.8 mm).")

        self.spinContacts = qt.QSpinBox()
        self.spinContacts.setRange(4, 18)
        self.spinContacts.setValue(10)
        self.spinContacts.setToolTip("Número de contactos activos de registro (anillos de platino-iridio).")

        self.spinBoltLength = qt.QDoubleSpinBox()
        self.spinBoltLength.setRange(5.0, 30.0)
        self.spinBoltLength.setValue(15.0)
        self.spinBoltLength.setSingleStep(1.0)
        self.spinBoltLength.setSuffix(" mm")
        self.spinBoltLength.setToolTip("Longitud del perno guía en el anclaje óseo craneal.")

        electrodeParamsLayout.addWidget(qt.QLabel("Diám:"))
        electrodeParamsLayout.addWidget(self.spinDiameter)
        electrodeParamsLayout.addWidget(qt.QLabel("Contactos:"))
        electrodeParamsLayout.addWidget(self.spinContacts)
        electrodeParamsLayout.addWidget(qt.QLabel("Perno:"))
        electrodeParamsLayout.addWidget(self.spinBoltLength)
        trajLayout.addRow("Calibre & Perno:", electrodeParamsLayout)

        self.chkRenderTube = qt.QCheckBox("Generar modelo 3D tubular y perno guía (volumen milimétrico)")
        self.chkRenderTube.setChecked(True)
        self.chkRenderTube.setToolTip("Crea la malla 3D volumétrica del electrodo y el cilindro de anclaje óseo.")
        trajLayout.addRow(self.chkRenderTube)

        self.btnComputeTrajectory = qt.QPushButton("Trazar y Añadir al Cuadro de Mandos")
        self.btnComputeTrajectory.setStyleSheet("font-weight: bold; background-color: #2b7a4b; color: white;")
        trajLayout.addRow(self.btnComputeTrajectory)

        self.lblMetrics = qt.QLabel("Estado: Esperando selección de puntos.")
        self.lblMetrics.setWordWrap(True)
        trajLayout.addRow("Métricas:", self.lblMetrics)

        # ---------------------------------------------------------------------
        # 4. Sección: Cuadro de Mandos Clínico & Seguridad Multi-Electrodo
        # ---------------------------------------------------------------------
        self.dashboardCollapsibleButton = ctk.ctkCollapsibleButton()
        self.dashboardCollapsibleButton.text = "4. Cuadro de Mandos Clínico & Seguridad Multi-Electrodo"
        parametersLayout.addWidget(self.dashboardCollapsibleButton)

        dashboardLayout = qt.QVBoxLayout(self.dashboardCollapsibleButton)

        self.lblDashboardSummary = qt.QLabel("Electrodos planificados: 0 | Seguros: 0 | En alerta: 0")
        self.lblDashboardSummary.setStyleSheet(
            "font-weight: bold; padding: 5px; background-color: #e9ecef; border: 1px solid #ced4da; border-radius: 4px;"
        )
        dashboardLayout.addWidget(self.lblDashboardSummary)

        self.trajectoriesTableWidget = qt.QTableWidget()
        self.trajectoriesTableWidget.setColumnCount(7)
        self.trajectoriesTableWidget.setHorizontalHeaderLabels(
            ["ID / Nombre", "Entrada (RAS)", "Diana (RAS)", "Long (mm)", "Ángulo Óseo", "Contactos", "Seguridad"]
        )
        self.trajectoriesTableWidget.horizontalHeader().setStretchLastSection(True)
        self.trajectoriesTableWidget.setSelectionBehavior(qt.QAbstractItemView.SelectRows)
        self.trajectoriesTableWidget.setSelectionMode(qt.QAbstractItemView.SingleSelection)
        self.trajectoriesTableWidget.setMinimumHeight(140)
        dashboardLayout.addWidget(self.trajectoriesTableWidget)

        dashboardBtnsLayout = qt.QHBoxLayout()
        self.btnFocusTrajectory = qt.QPushButton("Recentrar Vistas en Electrodo")
        self.btnFocusTrajectory.setStyleSheet("font-weight: bold;")
        self.btnRemoveTrajectory = qt.QPushButton("Eliminar Electrodo")
        self.btnRemoveTrajectory.setStyleSheet("color: white; background-color: #c0392b; font-weight: bold;")
        self.btnCheckConflicts = qt.QPushButton("Evaluar Conflictos Multi-Electrodo")
        self.btnCheckConflicts.setStyleSheet("font-weight: bold; background-color: #8c5b23; color: white;")
        dashboardBtnsLayout.addWidget(self.btnFocusTrajectory)
        dashboardBtnsLayout.addWidget(self.btnRemoveTrajectory)
        dashboardBtnsLayout.addWidget(self.btnCheckConflicts)
        dashboardLayout.addLayout(dashboardBtnsLayout)

        dashboardLayout.addWidget(qt.QLabel("<b>Contactos de Registro del Electrodo Seleccionado:</b>"))
        self.contactsTableWidget = qt.QTableWidget()
        self.contactsTableWidget.setColumnCount(3)
        self.contactsTableWidget.setHorizontalHeaderLabels(["Contacto", "Posición RAS (mm)", "Dist. Diana (mm)"])
        self.contactsTableWidget.horizontalHeader().setStretchLastSection(True)
        self.contactsTableWidget.setMaximumHeight(115)
        dashboardLayout.addWidget(self.contactsTableWidget)

        # ---------------------------------------------------------------------
        # 5. Sección: Exportación Quirúrgica & OpenIGTLink
        # ---------------------------------------------------------------------
        self.exportCollapsibleButton = ctk.ctkCollapsibleButton()
        self.exportCollapsibleButton.text = "5. Exportación Quirúrgica & OpenIGTLink"
        parametersLayout.addWidget(self.exportCollapsibleButton)

        exportLayout = qt.QFormLayout(self.exportCollapsibleButton)

        self.patientIdInput = qt.QLineEdit("ANON_PATIENT_01")
        exportLayout.addRow("Identificador Paciente:", self.patientIdInput)

        self.coordSystemSelector = qt.QComboBox()
        self.coordSystemSelector.addItem("RAS (3D Slicer / Nativo)", "RAS")
        self.coordSystemSelector.addItem("LPS (DICOM / Robótica / ROSA)", "LPS")
        exportLayout.addRow("Sistema Coordenadas:", self.coordSystemSelector)

        # Subsección A: Exportación a archivo local
        self.exportFormatSelector = qt.QComboBox()
        self.exportFormatSelector.addItem("JSON Estructurado (*.json)", "json")
        self.exportFormatSelector.addItem("CSV Quirúrgico Resumen (*.csv)", "csv_summary")
        self.exportFormatSelector.addItem("CSV Detallado con Contactos (*.csv)", "csv_detailed")
        self.exportFormatSelector.addItem("Slicer Markups JSON (*.mrk.json)", "markups")
        exportLayout.addRow("Formato de Exportación:", self.exportFormatSelector)

        self.btnExportFile = qt.QPushButton("Exportar Plan a Archivo")
        self.btnExportFile.toolTip = "Guarda las trayectorias y contactos en el formato seleccionado."
        exportLayout.addRow(self.btnExportFile)

        # Subsección B: Transmisión OpenIGTLink en red
        self.igtlHostInput = qt.QLineEdit("127.0.0.1")
        exportLayout.addRow("Servidor OpenIGTLink IP:", self.igtlHostInput)

        self.igtlPortInput = qt.QSpinBox()
        self.igtlPortInput.setRange(1024, 65535)
        self.igtlPortInput.setValue(18944)
        exportLayout.addRow("Puerto OpenIGTLink:", self.igtlPortInput)

        self.igtlTimeoutInput = qt.QDoubleSpinBox()
        self.igtlTimeoutInput.setRange(0.5, 10.0)
        self.igtlTimeoutInput.setSingleStep(0.5)
        self.igtlTimeoutInput.setValue(2.0)
        self.igtlTimeoutInput.setSuffix(" s")
        exportLayout.addRow("Timeout Conexión:", self.igtlTimeoutInput)

        self.btnTransmitIGTL = qt.QPushButton("Transmitir a Neuronavegador (OpenIGTLink)")
        self.btnTransmitIGTL.toolTip = "Envía transformaciones y puntos de trayectorias en tiempo real mediante OpenIGTLink."
        exportLayout.addRow(self.btnTransmitIGTL)

        self.lblIGTLStatus = qt.QLabel("Estado OpenIGTLink: Desconectado")
        self.lblIGTLStatus.setStyleSheet("color: #7f8c8d; font-style: italic;")
        exportLayout.addRow(self.lblIGTLStatus)

        parametersLayout.addStretch(1)

        # Conexión de señales y slots
        self.volumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onVolumeChanged)
        self.btnCenterViews.connect("clicked(bool)", self.onCenterViews)
        self.btnCreateTemplateLandmarks.connect("clicked(bool)", self.onCreateTemplateLandmarks)
        self.btnPlaceNz.connect("clicked(bool)", lambda: self.onPlaceLandmark("Nasion"))
        self.btnPlaceIz.connect("clicked(bool)", lambda: self.onPlaceLandmark("Inion"))
        self.btnPlaceLPA.connect("clicked(bool)", lambda: self.onPlaceLandmark("LPA"))
        self.btnPlaceRPA.connect("clicked(bool)", lambda: self.onPlaceLandmark("RPA"))
        self.btnGenerateHeadSurface.connect("clicked(bool)", self.onGenerateHeadSurface)
        self.btnCompute1020.connect("clicked(bool)", self.onCompute1020)
        self.btnExtractTargets.connect("clicked(bool)", self.onExtractTargets)
        self.btnComputeTrajectory.connect("clicked(bool)", self.onComputeTrajectory)
        self.btnCheckConflicts.connect("clicked(bool)", self.onCheckConflicts)
        self.btnFocusTrajectory.connect("clicked(bool)", self.onFocusTrajectory)
        self.btnRemoveTrajectory.connect("clicked(bool)", self.onRemoveTrajectory)
        self.trajectoriesTableWidget.connect("itemSelectionChanged()", self.onTrajectorySelectionChanged)
        self.btnExportFile.connect("clicked(bool)", self.onExportFile)
        self.btnTransmitIGTL.connect("clicked(bool)", self.onTransmitOpenIGTLink)

    def onVolumeChanged(self) -> None:
        """Inspecciona y valida el volumen MRI seleccionado."""
        volNode = self.volumeSelector.currentNode()
        if not volNode:
            self.lblVolumeInfo.setText("Estado: Ningún volumen MRI seleccionado.")
            return

        res = self.logic.validateAndInspectVolume(volNode)
        if isinstance(res, Ok):
            meta = res.value
            color = "#1e7e34" if meta.is_stereotaxy_optimal else "#d39e00"
            spc = meta.spacing_mm
            self.lblVolumeInfo.setText(
                f"<b>Dimensiones:</b> {meta.dimensions[0]}x{meta.dimensions[1]}x{meta.dimensions[2]} vóxeles<br>"
                f"<b>Espaciado:</b> {spc[0]:.2f} x {spc[1]:.2f} x {spc[2]:.2f} mm "
                f"(Vol: {meta.voxel_volume_mm3:.2f} mm³)<br>"
                f"<span style='color:{color};'><b>Calidad:</b> {meta.quality_notes}</span>"
            )
        else:
            self.lblVolumeInfo.setText(f"<span style='color:#c0392b;'>Error: {res.message}</span>")

    def onCenterViews(self) -> None:
        """Ajusta y centra los cortes ortogonales de visualización 2D sobre el volumen activo."""
        volNode = self.volumeSelector.currentNode()
        if not volNode:
            slicer.util.warningDisplay("Seleccione un volumen MRI para centrar las vistas.", windowTitle="Aviso")
            return

        res = self.logic.alignAndCenterVolume(volNode)
        if isinstance(res, Ok):
            slicer.util.infoDisplay(res.value, windowTitle="Vistas Centradas")
        else:
            slicer.util.errorDisplay(res.message, windowTitle="Error Centrado")

    def onCreateTemplateLandmarks(self) -> None:
        """Crea en la escena un nodo con 4 puntos de referencia iniciales."""
        node = self.logic.createTemplateLandmarksNode()
        if node is not None:
            self.refFiducialsSelector.setCurrentNode(node)
            slicer.util.infoDisplay(
                "Plantilla de fiduciales creada. Posicione los 4 puntos (Nasion, Inion, LPA, RPA) sobre el paciente.",
                windowTitle="SEEGPlanner",
            )

    def onPlaceLandmark(self, landmark_name: str) -> None:
        """Activa el modo interactivo de colocación de puntos en Slicer para la referencia seleccionada."""
        refNode = self.refFiducialsSelector.currentNode()
        if not refNode:
            refNode = self.logic.createTemplateLandmarksNode()
            if refNode:
                self.refFiducialsSelector.setCurrentNode(refNode)

        if slicer is not None and hasattr(slicer, "modules") and hasattr(slicer.modules, "markups"):
            slicer.modules.markups.logic().SetActiveListID(refNode)
            interactionNode = slicer.app.applicationLogic().GetInteractionNode()
            interactionNode.SetCurrentInteractionMode(slicer.vtkMRMLInteractionNode.Place)
            slicer.util.infoDisplay(
                f"Modo colocación activo: Haga clic en la vista 3D o cortes para situar '{landmark_name}'.",
                windowTitle="SEEGPlanner",
            )

    def onGenerateHeadSurface(self) -> None:
        """Genera el modelo 3D poligonal de la superficie de la cabeza a partir del volumen MRI."""
        volNode = self.volumeSelector.currentNode()
        if not volNode:
            slicer.util.errorDisplay("Seleccione primero un volumen MRI en la Sección 1.", windowTitle="Error")
            return

        res = self.logic.generateHeadSurfaceModel(volNode)
        if isinstance(res, Ok):
            modelNode = res.value
            self.headSurfaceSelector.setCurrentNode(modelNode)
            slicer.util.infoDisplay(
                "Superficie 3D de la cabeza generada exitosamente mediante Marching Cubes / Flying Edges.",
                windowTitle="Superficie Generada",
            )
        else:
            slicer.util.errorDisplay(f"Error generando superficie: {res.message}", windowTitle="Error")

    def onCompute1020(self) -> None:
        """Invoca el cálculo geométrico y la proyección de la rejilla 10-20 a partir del nodo de referencias."""
        refNode = self.refFiducialsSelector.currentNode()
        if not refNode:
            slicer.util.errorDisplay("Debe seleccionar un nodo con los fiduciales de referencia.", windowTitle="Error")
            return

        headModel = self.headSurfaceSelector.currentNode() if self.chkProjectOnSurface.isChecked() else None

        result = self.logic.compute1020Grid(refNode, headModelNode=headModel)
        if isinstance(result, Ok):
            mode_str = "proyectados sobre la superficie 3D" if headModel else "analíticos esféricos"
            slicer.util.infoDisplay(
                f"Rejilla EEG 10-20 calculada con éxito ({len(result.value)} electrodos {mode_str}).",
                windowTitle="Éxito 10-20",
            )
        else:
            slicer.util.errorDisplay(f"Error al calcular sistema 10-20: {result.message}", windowTitle="Error 10-20")

    def onExtractTargets(self) -> None:
        """Extrae los centroides 3D de cada segmento anatómico y puebla la tabla y selector de diana."""
        segNode = self.segmentationSelector.currentNode()
        refVol = self.volumeSelector.currentNode()

        if not segNode:
            slicer.util.errorDisplay("Seleccione un nodo de segmentación cerebral.", windowTitle="Error")
            return

        result = self.logic.extractTargetsFromSegmentation(segNode, refVol)
        if isinstance(result, Ok):
            targets = result.value
            self.extracted_targets = targets
            self.targetsTableWidget.setRowCount(len(targets))

            for row, tgt in enumerate(targets):
                self.targetsTableWidget.setItem(row, 0, qt.QTableWidgetItem(tgt.name))
                self.targetsTableWidget.setItem(row, 1, qt.QTableWidgetItem(str(tgt.volume_mm3)))
                c_str = f"({tgt.contained_point_ras[0]}, {tgt.contained_point_ras[1]}, {tgt.contained_point_ras[2]})"
                self.targetsTableWidget.setItem(row, 2, qt.QTableWidgetItem(c_str))
                inside_str = "Sí" if tgt.is_centroid_inside_mask else "Ajustado"
                self.targetsTableWidget.setItem(row, 3, qt.QTableWidgetItem(inside_str))

            # Conectar el nodo de fiduciales de diana al selector de dianas
            targetFidNode = slicer.mrmlScene.GetFirstNodeByName("SEEG_Targets")
            if targetFidNode:
                self.targetPointSelector.setCurrentNode(targetFidNode)

            slicer.util.infoDisplay(
                f"Se han extraído con éxito {len(targets)} dianas anatómicas tridimensionales.",
                windowTitle="Dianas Extraídas",
            )
        else:
            slicer.util.errorDisplay(f"Error en extracción de dianas: {result.message}", windowTitle="Error")

    def onComputeTrajectory(self) -> None:
        """Calcula el vector de trayectoria, modelo 3D y distribución de contactos entre entrada y diana."""
        entryNode = self.entryPointSelector.currentNode()
        targetNode = self.targetPointSelector.currentNode()

        if not entryNode or not targetNode:
            slicer.util.errorDisplay("Seleccione nodos válidos para Entrada y Diana.", windowTitle="Atención")
            return

        cfg = ElectrodeConfig(
            diameter_mm=self.spinDiameter.value,
            num_contacts=self.spinContacts.value,
            bolt_length_mm=self.spinBoltLength.value,
        )
        render_tube = self.chkRenderTube.isChecked
        electrode_idx = len(self.planned_trajectories) + 1
        traj_name = f"SEEG_Elec_{electrode_idx:02d}"

        result = self.logic.computeTrajectoryBetweenNodes(
            entryNode,
            targetNode,
            config=cfg,
            renderTube=render_tube,
            electrodeName=traj_name,
        )
        if isinstance(result, Ok):
            metrics = result.value
            self.planned_trajectories.append(metrics)
            self.refreshTrajectoriesTable()
            last_row = len(self.planned_trajectories) - 1
            self.trajectoriesTableWidget.selectRow(last_row)

            status_color = "#1e7e34" if metrics.is_safe else "#d39e00"
            contacts_count = len(metrics.contacts)
            self.lblMetrics.setText(
                f"<b>Electrodo:</b> {metrics.name} (Calibre {cfg.diameter_mm:.1f} mm, {contacts_count} contactos)<br>"
                f"<b>Longitud total:</b> {metrics.length_mm} mm<br>"
                f"<b>Ángulo con normal ósea:</b> {metrics.angle_degrees or 'N/A'}°<br>"
                f"<b>Seguridad:</b> <span style='color:{status_color}; font-weight:bold;'>{metrics.status_message}</span>"
            )
            slicer.util.infoDisplay(
                f"Trayectoria '{metrics.name}' planificada y añadida al cuadro de mandos.\n"
                f"- Longitud: {metrics.length_mm} mm\n"
                f"- Desviación ósea: {metrics.angle_degrees or 'N/A'}°\n"
                f"- Contactos activos: {contacts_count}\n"
                f"- Estado: {metrics.status_message}",
                windowTitle="Trayectoria Planificada",
            )
        else:
            slicer.util.errorDisplay(f"Fallo en cálculo: {result.message}", windowTitle="Error Trayectoria")

    def refreshTrajectoriesTable(self) -> None:
        """Actualiza la tabla del cuadro de mandos con el estado y semáforo de las trayectorias."""
        self._isUpdatingUI = True
        self.trajectoriesTableWidget.blockSignals(True)

        n_traj = len(self.planned_trajectories)
        self.trajectoriesTableWidget.setRowCount(n_traj)

        safe_count = 0
        alert_count = 0

        for row, traj in enumerate(self.planned_trajectories):
            self.trajectoriesTableWidget.setItem(row, 0, qt.QTableWidgetItem(traj.name))
            e_str = f"({traj.entry_point[0]:.1f}, {traj.entry_point[1]:.1f}, {traj.entry_point[2]:.1f})"
            self.trajectoriesTableWidget.setItem(row, 1, qt.QTableWidgetItem(e_str))
            t_str = f"({traj.target_point[0]:.1f}, {traj.target_point[1]:.1f}, {traj.target_point[2]:.1f})"
            self.trajectoriesTableWidget.setItem(row, 2, qt.QTableWidgetItem(t_str))
            self.trajectoriesTableWidget.setItem(row, 3, qt.QTableWidgetItem(f"{traj.length_mm:.1f}"))
            ang_str = f"{traj.angle_degrees:.1f}°" if traj.angle_degrees is not None else "N/A"
            self.trajectoriesTableWidget.setItem(row, 4, qt.QTableWidgetItem(ang_str))
            self.trajectoriesTableWidget.setItem(row, 5, qt.QTableWidgetItem(str(len(traj.contacts))))

            # Estado semafórico
            status_item = qt.QTableWidgetItem()
            if traj.is_safe:
                safe_count += 1
                status_item.setText("SEGURO (≤30°)")
                status_item.setForeground(qt.QColor("#1e7e34"))
            else:
                alert_count += 1
                status_item.setText(f"ALERTA ({ang_str})")
                status_item.setForeground(qt.QColor("#d39e00"))

            self.trajectoriesTableWidget.setItem(row, 6, status_item)

        self.lblDashboardSummary.setText(
            f"Electrodos planificados: {n_traj} | Seguros: {safe_count} | En alerta de perno: {alert_count}"
        )

        self.trajectoriesTableWidget.blockSignals(False)
        self._isUpdatingUI = False

    def onTrajectorySelectionChanged(self) -> None:
        """Actualiza el visor de contactos cuando el usuario selecciona un electrodo en la tabla."""
        if self._isUpdatingUI:
            return

        selected_rows = self.trajectoriesTableWidget.selectionModel().selectedRows()
        if not selected_rows:
            self.contactsTableWidget.setRowCount(0)
            return

        row = selected_rows[0].row()
        if row < 0 or row >= len(self.planned_trajectories):
            self.contactsTableWidget.setRowCount(0)
            return

        traj = self.planned_trajectories[row]
        contacts = traj.contacts

        self.contactsTableWidget.setRowCount(len(contacts))
        for c_idx, c in enumerate(contacts):
            self.contactsTableWidget.setItem(c_idx, 0, qt.QTableWidgetItem(c.label))
            pos_str = f"({c.position_ras[0]:.2f}, {c.position_ras[1]:.2f}, {c.position_ras[2]:.2f})"
            self.contactsTableWidget.setItem(c_idx, 1, qt.QTableWidgetItem(pos_str))
            self.contactsTableWidget.setItem(c_idx, 2, qt.QTableWidgetItem(f"{c.distance_from_tip_mm:.2f} mm"))

    def onFocusTrajectory(self) -> None:
        """Centra los cortes ortogonales de visualización 2D sobre el electrodo seleccionado."""
        selected_rows = self.trajectoriesTableWidget.selectionModel().selectedRows()
        if not selected_rows:
            slicer.util.warningDisplay("Seleccione un electrodo de la tabla para recentrar.", windowTitle="Aviso")
            return

        row = selected_rows[0].row()
        if 0 <= row < len(self.planned_trajectories):
            traj = self.planned_trajectories[row]
            res = self.logic.focusTrajectoryInViews(traj)
            if isinstance(res, Ok):
                slicer.util.infoDisplay(res.value, windowTitle="Vistas Centradas")

    def onRemoveTrajectory(self) -> None:
        """Elimina de forma atómica y limpia el electrodo seleccionado en la memoria y en la escena MRML."""
        selected_rows = self.trajectoriesTableWidget.selectionModel().selectedRows()
        if not selected_rows:
            slicer.util.warningDisplay("Seleccione un electrodo de la tabla para eliminar.", windowTitle="Aviso")
            return

        row = selected_rows[0].row()
        if 0 <= row < len(self.planned_trajectories):
            traj_name = self.planned_trajectories[row].name
            res = self.logic.removePlannedTrajectoryByIndex(row, self.planned_trajectories)
            if isinstance(res, Ok):
                self.refreshTrajectoriesTable()
                self.contactsTableWidget.setRowCount(0)
                self.lblMetrics.setText(f"Electrodo '{traj_name}' eliminado del plan quirúrgico.")
                slicer.util.infoDisplay(
                    f"Electrodo '{traj_name}' y sus geometrías 3D purgados de la escena MRML con éxito.",
                    windowTitle="Electrodo Eliminado",
                )
            else:
                slicer.util.errorDisplay(f"Error al eliminar electrodo: {res.message}", windowTitle="Error")

    def onCheckConflicts(self) -> None:
        """Evalúa los conflictos espaciales y de colisión entre todas las trayectorias planificadas."""
        if len(self.planned_trajectories) < 2:
            slicer.util.warningDisplay(
                "Se requieren al menos 2 trayectorias planificadas para evaluar conflictos multi-electrodo.",
                windowTitle="Aviso de Conflictos",
            )
            return

        conflicts_res = self.logic.checkPlannedConflicts(self.planned_trajectories)
        if isinstance(conflicts_res, Ok):
            conflicts = conflicts_res.value
            if not conflicts:
                slicer.util.infoDisplay(
                    f"Evaluación completada sin conflictos en {len(self.planned_trajectories)} electrodos.\n"
                    "Todas las distancias entre pernos craneales son >= 10.0 mm y "
                    "las distancias intracraneales son >= 3.0 mm.",
                    windowTitle="Seguridad Multi-Electrodo",
                )
            else:
                crit_count = sum(1 for c in conflicts if c.is_critical)
                msg_lines = [f"Se detectaron {len(conflicts)} alerta(s) ({crit_count} crítica(s)):"]
                for c in conflicts:
                    crit_prefix = "[CRÍTICO] " if c.is_critical else "[ALERTA] "
                    msg_lines.append(f"• {crit_prefix}{c.description}")
                slicer.util.warningDisplay("\n".join(msg_lines), windowTitle="Conflicto entre Electrodos")
        else:
            slicer.util.errorDisplay(f"Error evaluando conflictos: {conflicts_res.message}", windowTitle="Error")

    def onExportFile(self) -> None:
        """Exporta el conjunto de trayectorias planificadas al formato seleccionado (JSON, CSV, Markups)."""
        if not self.planned_trajectories:
            slicer.util.warningDisplay("No hay trayectorias planificadas para exportar.", windowTitle="Aviso")
            return

        fmt_id = self.exportFormatSelector.currentData or "json"
        coord_sys = self.coordSystemSelector.currentData or "RAS"
        pat_id = self.patientIdInput.text or "ANONYMIZED_PATIENT"

        dialog = qt.QFileDialog()
        dialog.setFileMode(qt.QFileDialog.AnyFile)
        dialog.setAcceptMode(qt.QFileDialog.AcceptSave)

        if fmt_id == "json":
            dialog.setNameFilter("Archivos JSON (*.json)")
            dialog.setDefaultSuffix("json")
        elif fmt_id in ("csv_summary", "csv_detailed"):
            dialog.setNameFilter("Archivos CSV (*.csv)")
            dialog.setDefaultSuffix("csv")
        elif fmt_id == "markups":
            dialog.setNameFilter("Slicer Markups JSON (*.mrk.json)")
            dialog.setDefaultSuffix("mrk.json")

        if dialog.exec_():
            filepaths = dialog.selectedFiles()
            if filepaths:
                out_path = filepaths[0]
                export_res = self.logic.exportPlanToFile(
                    self.planned_trajectories,
                    out_path,
                    file_format=fmt_id,
                    coordinate_system=coord_sys,
                    patient_id=pat_id,
                )
                if isinstance(export_res, Ok):
                    slicer.util.infoDisplay(export_res.value, windowTitle="Exportación Completa")
                else:
                    slicer.util.errorDisplay(f"Error al exportar archivo: {export_res.message}", windowTitle="Error")

    def onTransmitOpenIGTLink(self) -> None:
        """Transmite las trayectorias mediante protocolo OpenIGTLink al neuronavegador o simulador."""
        if not self.planned_trajectories:
            slicer.util.warningDisplay(
                "No hay trayectorias planificadas para transmitir por OpenIGTLink.",
                windowTitle="Aviso",
            )
            return

        host = self.igtlHostInput.text.strip() or "127.0.0.1"
        port = int(self.igtlPortInput.value)
        timeout = float(self.igtlTimeoutInput.value)
        coord_sys = self.coordSystemSelector.currentData or "RAS"

        self.lblIGTLStatus.setText(f"Estado OpenIGTLink: Conectando a {host}:{port}...")
        self.lblIGTLStatus.setStyleSheet("color: #d39e00; font-weight: bold;")
        if slicer is not None and hasattr(slicer, "app") and slicer.app is not None:
            slicer.app.processEvents()

        res = self.logic.transmitPlanViaOpenIGTLink(
            self.planned_trajectories,
            host=host,
            port=port,
            timeout_sec=timeout,
            coordinate_system=coord_sys,
        )

        if isinstance(res, Ok):
            stats = res.value
            total_b = stats.get("total_bytes_sent", 0)
            msg = (
                f"Transmisión exitosa a {host}:{port} ({coord_sys}).\n"
                f"• Mensajes TRANSFORM: {stats.get('transforms_sent', 0)}\n"
                f"• Mensajes POINT: {stats.get('points_sent', 0)}\n"
                f"• Total bytes enviados: {total_b}"
            )
            self.lblIGTLStatus.setText(f"Estado OpenIGTLink: Transmitido con éxito ({total_b} B)")
            self.lblIGTLStatus.setStyleSheet("color: #1e7e34; font-weight: bold;")
            slicer.util.infoDisplay(msg, windowTitle="OpenIGTLink Transmisión Exitosa")
        else:
            self.lblIGTLStatus.setText("Estado OpenIGTLink: Error de conexión")
            self.lblIGTLStatus.setStyleSheet("color: #c0392b; font-weight: bold;")
            slicer.util.errorDisplay(res.message, windowTitle="Error de Conexión OpenIGTLink")


class SEEGPlannerLogic(ScriptedLoadableModuleLogic):
    """Lógica central desacoplada para interacción con la escena MRML y orquestación algorítmica."""

    def validateAndInspectVolume(self, volumeNode: Any) -> Result[VolumeMetadata]:
        """Inspecciona las propiedades geométricas y calidad diagnóstica del volumen MRI."""
        if volumeNode is None:
            return Err("El nodo de volumen es nulo.")

        imgData = volumeNode.GetImageData() if hasattr(volumeNode, "GetImageData") else None
        if imgData is None:
            return Err("El volumen seleccionado no posee datos de imagen válidos.")

        dims = imgData.GetDimensions()
        spc = volumeNode.GetSpacing()

        res = validate_volume_metadata(dimensions=dims, spacing_mm=spc)
        return res

    def alignAndCenterVolume(self, volumeNode: Any) -> Result[str]:
        """Recentra las vistas ortogonales 2D sobre el centro del volumen neuroanatómico."""
        if volumeNode is None:
            return Err("Nodo de volumen no especificado.")

        if slicer is not None and hasattr(slicer, "app") and slicer.app.layoutManager() is not None:
            layoutManager = slicer.app.layoutManager()
            for sliceColor in ["Red", "Yellow", "Green"]:
                sliceWidget = layoutManager.sliceWidget(sliceColor)
                if sliceWidget is not None:
                    sliceWidget.sliceController().fitSliceToBackground()
            resultado: Result[str] = Ok("Vistas ortogonales ajustadas y centradas sobre el volumen.")
        else:
            resultado = Ok("Recentrado simulado (entorno headless sin GUI).")

        return resultado

    def generateHeadSurfaceModel(self, volumeNode: Any, thresholdRatio: float = 0.15) -> Result[Any]:
        """Genera el modelo 3D poligonal de la cabeza del paciente (Head_Surface) mediante FlyingEdges/MarchingCubes."""
        if volumeNode is None:
            return Err("Nodo de volumen MRI no especificado.")

        imgData = volumeNode.GetImageData() if hasattr(volumeNode, "GetImageData") else None
        if imgData is None:
            return Err("El volumen seleccionado no posee datos de imagen volumétrica.")

        ijk_to_ras = np.eye(4, dtype=np.float64)
        if hasattr(volumeNode, "GetIJKToRASMatrix") and vtk is not None:
            vmat = vtk.vtkMatrix4x4()
            volumeNode.GetIJKToRASMatrix(vmat)
            for r in range(4):
                for c in range(4):
                    ijk_to_ras[r, c] = vmat.GetElement(r, c)

        params = SurfaceExtractionParams(threshold_ratio=thresholdRatio)
        res_poly = extract_head_surface_polydata(imgData, ijk_to_ras, params)
        if isinstance(res_poly, Err):
            return res_poly

        polydata = res_poly.value

        if slicer is not None and hasattr(slicer, "mrmlScene") and slicer.mrmlScene is not None:
            modelNode = slicer.mrmlScene.GetFirstNodeByName("Head_Surface")
            if modelNode is None:
                modelNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", "Head_Surface")
                modelNode.CreateDefaultDisplayNodes()

            modelNode.SetAndObservePolyData(polydata)
            dispNode = modelNode.GetDisplayNode()
            if dispNode is not None:
                dispNode.SetColor(0.88, 0.76, 0.65)  # Tono piel natural
                dispNode.SetOpacity(0.70)             # Semitransparencia quirúrgica
                dispNode.SetBackfaceCulling(True)

            resultado: Result[Any] = Ok(modelNode)
        else:
            resultado = Ok(polydata)

        return resultado

    def createTemplateLandmarksNode(self) -> Any:
        """Genera un nodo `vtkMRMLMarkupsFiducialNode` con las 4 referencias canónicas pre-etiquetadas."""
        if slicer is None or not hasattr(slicer, "mrmlScene") or slicer.mrmlScene is None:
            return None

        fidNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", "AnatomicalLandmarks_Nz_Iz_LPA_RPA")
        fidNode.AddControlPoint([0.0, 90.0, -10.0], "Nasion")
        fidNode.AddControlPoint([0.0, -110.0, -30.0], "Inion")
        fidNode.AddControlPoint([-75.0, -10.0, -40.0], "LPA")
        fidNode.AddControlPoint([75.0, -10.0, -40.0], "RPA")
        return fidNode

    def compute1020Grid(
        self,
        refFiducialNode: Any,
        headModelNode: Any = None,
    ) -> Result[Dict[str, Tuple[float, float, float]]]:
        """Extrae coordenadas de Nz, Iz, LPA, RPA y crea/proyecta el nodo con la rejilla 10-20 calculada."""
        if refFiducialNode is None or refFiducialNode.GetNumberOfControlPoints() < 4:
            return Err("El nodo debe contener al menos 4 puntos de control (Nasion, Inion, LPA, RPA).")

        points_by_label: Dict[str, Tuple[float, float, float]] = {}
        for i in range(refFiducialNode.GetNumberOfControlPoints()):
            label = refFiducialNode.GetNthControlPointLabel(i).strip().upper()
            pos = [0.0, 0.0, 0.0]
            refFiducialNode.GetNthControlPointPosition(i, pos)
            coords = (float(pos[0]), float(pos[1]), float(pos[2]))

            if "NASION" in label or label == "NZ":
                points_by_label["Nz"] = coords
            elif "INION" in label or label == "IZ":
                points_by_label["Iz"] = coords
            elif "LPA" in label:
                points_by_label["LPA"] = coords
            elif "RPA" in label:
                points_by_label["RPA"] = coords

        if len(points_by_label) < 4:
            pts: List[Tuple[float, float, float]] = []
            for i in range(4):
                pos = [0.0, 0.0, 0.0]
                refFiducialNode.GetNthControlPointPosition(i, pos)
                pts.append((float(pos[0]), float(pos[1]), float(pos[2])))
            landmarks = CanonicalLandmarks(nasion=pts[0], inion=pts[1], lpa=pts[2], rpa=pts[3])
        else:
            landmarks = CanonicalLandmarks(
                nasion=points_by_label["Nz"],
                inion=points_by_label["Iz"],
                lpa=points_by_label["LPA"],
                rpa=points_by_label["RPA"],
            )

        calc_result = calculate_1020_points(landmarks)
        if isinstance(calc_result, Err):
            return calc_result

        final_points = calc_result.value

        # Proyección sobre superficie poligonal si existe
        polydata = None
        if headModelNode is not None and hasattr(headModelNode, "GetPolyData"):
            polydata = headModelNode.GetPolyData()
        elif slicer is not None and hasattr(slicer, "mrmlScene") and slicer.mrmlScene is not None:
            headNode = slicer.mrmlScene.GetFirstNodeByName("Head_Surface")
            if headNode is not None and hasattr(headNode, "GetPolyData"):
                polydata = headNode.GetPolyData()

        if polydata is not None and polydata.GetNumberOfPoints() > 0:
            p_nz = np.array(landmarks.nasion, dtype=np.float64)
            p_iz = np.array(landmarks.inion, dtype=np.float64)
            p_lpa = np.array(landmarks.lpa, dtype=np.float64)
            p_rpa = np.array(landmarks.rpa, dtype=np.float64)
            center_tuple = (
                float((p_nz[0] + p_iz[0] + p_lpa[0] + p_rpa[0]) * 0.25),
                float((p_nz[1] + p_iz[1] + p_lpa[1] + p_rpa[1]) * 0.25),
                float((p_nz[2] + p_iz[2] + p_lpa[2] + p_rpa[2]) * 0.25),
            )
            proj_res = project_points_to_surface_mesh(final_points, polydata, center_tuple)
            if isinstance(proj_res, Ok):
                final_points = proj_res.value

        # Crear o actualizar el nodo de salida en la escena MRML
        if slicer is not None and hasattr(slicer, "mrmlScene") and slicer.mrmlScene is not None:
            gridNode = slicer.mrmlScene.GetFirstNodeByName("EEG_1020_Grid")
            if gridNode is None:
                gridNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", "EEG_1020_Grid")
            else:
                gridNode.RemoveAllControlPoints()

            dispNode = gridNode.GetDisplayNode()
            if dispNode is not None:
                dispNode.SetGlyphTypeFromString("Sphere3D")
                dispNode.SetGlyphScale(3.0)
                dispNode.SetSelectedColor(0.2, 0.8, 0.9)

            for electrode_name, coords in final_points.items():
                gridNode.AddControlPoint(list(coords), electrode_name)

        resultado_grid: Result[Dict[str, Tuple[float, float, float]]] = Ok(final_points)
        return resultado_grid

    def extractTargetsFromSegmentation(
        self,
        segmentationNode: Any,
        referenceVolumeNode: Any = None,
    ) -> Result[List[TargetStructure]]:
        """
        Extrae los centroides anatómicos de los segmentos y genera el nodo de marcas SEEG_Targets.
        """
        if segmentationNode is None:
            return Err("Nodo de segmentación no suministrado.")

        segmentation = segmentationNode.GetSegmentation()
        if segmentation is None or segmentation.GetNumberOfSegments() == 0:
            return Err("La segmentación está vacía o no contiene estructuras cerebrales.")

        # Obtener matriz IJK to RAS del volumen de referencia o identidad
        ijk_to_ras = np.eye(4, dtype=np.float64)
        if referenceVolumeNode is not None and hasattr(referenceVolumeNode, "GetIJKToRASMatrix"):
            vmat = vtk.vtkMatrix4x4()
            referenceVolumeNode.GetIJKToRASMatrix(vmat)
            for r in range(4):
                for c in range(4):
                    ijk_to_ras[r, c] = vmat.GetElement(r, c)

        targets_extracted: List[TargetStructure] = []

        # Preparar nodo de fiduciales para las dianas
        targetsFidNode = None
        if slicer is not None and hasattr(slicer, "mrmlScene") and slicer.mrmlScene is not None:
            targetsFidNode = slicer.mrmlScene.GetFirstNodeByName("SEEG_Targets")
            if targetsFidNode is None:
                targetsFidNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", "SEEG_Targets")
            else:
                targetsFidNode.RemoveAllControlPoints()

            disp = targetsFidNode.GetDisplayNode()
            if disp is not None:
                disp.SetGlyphTypeFromString("Sphere3D")
                disp.SetGlyphScale(3.5)
                disp.SetSelectedColor(0.9, 0.4, 0.1)  # Naranja destacado

        for i in range(segmentation.GetNumberOfSegments()):
            segmentId = segmentation.GetNthSegmentID(i)
            segment = segmentation.GetSegment(segmentId)
            segmentName = segment.GetName() if segment else segmentId

            # Intentar extraer arreglo binario con utilidades de Slicer
            mask_arr = None
            if slicer is not None and hasattr(slicer, "util") and hasattr(slicer.util, "arrayFromSegmentBinaryLabelmap"):
                try:
                    mask_arr = slicer.util.arrayFromSegmentBinaryLabelmap(
                        segmentationNode, segmentId, referenceVolumeNode
                    )
                except Exception:
                    mask_arr = None

            # Si se obtuvo el array tridimensional
            if mask_arr is not None and mask_arr.ndim == 3 and np.any(mask_arr > 0):
                target_res = compute_segment_target(segmentId, segmentName, mask_arr, ijk_to_ras)
                if isinstance(target_res, Ok):
                    tgt = target_res.value
                    targets_extracted.append(tgt)
                    if targetsFidNode is not None:
                        targetsFidNode.AddControlPoint(list(tgt.contained_point_ras), f"Target_{tgt.name}")
            else:
                # Fallback: estimación basada en los bounds del segmento
                bounds = [0.0] * 6
                segmentation.GetSegment(segmentId).GetBounds(bounds)
                c_ras = (
                    round((bounds[0] + bounds[1]) * 0.5, 2),
                    round((bounds[2] + bounds[3]) * 0.5, 2),
                    round((bounds[4] + bounds[5]) * 0.5, 2),
                )
                bbox_min = (bounds[0], bounds[2], bounds[4])
                bbox_max = (bounds[1], bounds[3], bounds[5])
                dx = abs(bounds[1] - bounds[0])
                dy = abs(bounds[3] - bounds[2])
                dz = abs(bounds[5] - bounds[4])
                est_volume = round(dx * dy * dz * 0.52, 2)  # Aprox elipsoide

                tgt = TargetStructure(
                    segment_id=segmentId,
                    name=segmentName,
                    centroid_ras=c_ras,
                    contained_point_ras=c_ras,
                    volume_mm3=est_volume,
                    voxel_count=100,
                    is_centroid_inside_mask=True,
                    bounding_box_ras=(bbox_min, bbox_max),
                )
                targets_extracted.append(tgt)
                if targetsFidNode is not None:
                    targetsFidNode.AddControlPoint(list(c_ras), f"Target_{tgt.name}")

        resultado: Result[List[TargetStructure]] = Ok(targets_extracted)
        return resultado

    def computeTrajectoryBetweenNodes(
        self,
        entryNode: Any,
        targetNode: Any,
        config: ElectrodeConfig | None = None,
        renderTube: bool = True,
        electrodeName: str = "Trajectory_Planned",
    ) -> Result[TrajectoryMetrics]:
        """Calcula métricas estereotácticas, línea 3D y modelo tubular volumétrico con perno guía."""
        if entryNode is None or targetNode is None:
            return Err("Los nodos de entrada y diana deben existir.")

        if entryNode.GetNumberOfControlPoints() < 1 or targetNode.GetNumberOfControlPoints() < 1:
            return Err("Ambos nodos deben contener al menos un punto de control tridimensional.")

        pos_entry = [0.0, 0.0, 0.0]
        pos_target = [0.0, 0.0, 0.0]
        entryNode.GetNthControlPointPosition(0, pos_entry)
        targetNode.GetNthControlPointPosition(0, pos_target)

        entry_tuple = (float(pos_entry[0]), float(pos_entry[1]), float(pos_entry[2]))
        target_tuple = (float(pos_target[0]), float(pos_target[1]), float(pos_target[2]))

        # Obtener normal de superficie en punto de entrada si la superficie está disponible
        skull_normal = None
        if slicer is not None and hasattr(slicer, "mrmlScene") and slicer.mrmlScene is not None:
            headNode = slicer.mrmlScene.GetFirstNodeByName("Head_Surface")
            if headNode is not None and hasattr(headNode, "GetPolyData") and headNode.GetPolyData() is not None:
                norm_res = get_surface_normal_at_point(headNode.GetPolyData(), entry_tuple)
                if isinstance(norm_res, Ok):
                    skull_normal = norm_res.value

        cfg = config or ElectrodeConfig()

        traj_result = calculate_trajectory(
            entry_tuple,
            target_tuple,
            name=electrodeName,
            skull_normal=skull_normal,
            config=cfg,
        )
        if isinstance(traj_result, Err):
            return traj_result

        # 1. Representación visual como línea en la escena MRML
        if slicer is not None and hasattr(slicer, "mrmlScene") and slicer.mrmlScene is not None:
            lineNode = slicer.mrmlScene.GetFirstNodeByName(f"{electrodeName}_Line")
            if lineNode is None:
                lineNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsLineNode", f"{electrodeName}_Line")
            else:
                lineNode.RemoveAllControlPoints()

            lineNode.AddControlPoint(list(entry_tuple), "Entry")
            lineNode.AddControlPoint(list(target_tuple), "Target")
            displayNode = lineNode.GetDisplayNode()
            if displayNode is not None:
                displayNode.SetLineThickness(0.3)
                if traj_result.value.is_safe:
                    displayNode.SetSelectedColor(0.1, 0.85, 0.2)  # Verde
                else:
                    displayNode.SetSelectedColor(0.9, 0.7, 0.1)  # Amarillo/Alerta

            # 2. Representación como modelo 3D tubular con perno guía si se solicita
            if renderTube and vtk is not None:
                tube_res = generate_electrode_tube_polydata(entry_tuple, target_tuple, config=cfg)
                if isinstance(tube_res, Ok):
                    tube_poly = tube_res.value
                    modelNode = slicer.mrmlScene.GetFirstNodeByName(f"{electrodeName}_Model")
                    if modelNode is None:
                        modelNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", f"{electrodeName}_Model")
                        modelNode.CreateDefaultDisplayNodes()

                    modelNode.SetAndObservePolyData(tube_poly)
                    dispModel = modelNode.GetDisplayNode()
                    if dispModel is not None:
                        dispModel.SetOpacity(0.85)
                        if traj_result.value.is_safe:
                            dispModel.SetColor(0.2, 0.75, 0.3)  # Verde esmeralda
                        else:
                            dispModel.SetColor(0.95, 0.65, 0.15)  # Ámbar alerta

        resultado: Result[TrajectoryMetrics] = traj_result
        return resultado

    def checkPlannedConflicts(
        self,
        trajectories: Sequence[TrajectoryMetrics],
        minEntryDistMm: float = 10.0,
        minIntracranialDistMm: float = 3.0,
    ) -> Result[Tuple[TrajectoryConflict, ...]]:
        """Comprueba de forma global los conflictos espaciales y de pernos entre trayectorias planificadas."""
        res = check_trajectory_conflicts(
            trajectories,
            min_entry_dist_mm=minEntryDistMm,
            min_intracranial_dist_mm=minIntracranialDistMm,
        )
        return res

    def removePlannedTrajectoryByIndex(
        self,
        index: int,
        trajectories: List[TrajectoryMetrics],
    ) -> Result[TrajectoryMetrics]:
        """Elimina de forma atómica y sincronizada una trayectoria de la memoria y sus nodos de la escena MRML."""
        if index < 0 or index >= len(trajectories):
            return Err(f"Índice de trayectoria ({index}) fuera de rango (total: {len(trajectories)}).")

        traj_to_remove = trajectories[index]

        # Purgado explícito de nodos en la escena médica para evitar nodos fantasma
        if slicer is not None and hasattr(slicer, "mrmlScene") and slicer.mrmlScene is not None:
            lineNode = slicer.mrmlScene.GetFirstNodeByName(f"{traj_to_remove.name}_Line")
            if lineNode is not None:
                slicer.mrmlScene.RemoveNode(lineNode)

            modelNode = slicer.mrmlScene.GetFirstNodeByName(f"{traj_to_remove.name}_Model")
            if modelNode is not None:
                slicer.mrmlScene.RemoveNode(modelNode)

        removed = trajectories.pop(index)
        resultado: Result[TrajectoryMetrics] = Ok(removed)
        return resultado

    def focusTrajectoryInViews(self, traj: TrajectoryMetrics) -> Result[str]:
        """Centra los cortes ortogonales de Slicer en el punto medio de la trayectoria activa."""
        if traj is None:
            return Err("La métrica de trayectoria es nula.")

        midpoint = (
            (traj.entry_point[0] + traj.target_point[0]) * 0.5,
            (traj.entry_point[1] + traj.target_point[1]) * 0.5,
            (traj.entry_point[2] + traj.target_point[2]) * 0.5,
        )

        if slicer is not None and hasattr(slicer, "mrmlScene") and slicer.mrmlScene is not None:
            sliceNodes = slicer.mrmlScene.GetNodesByClass("vtkMRMLSliceNode")
            for i in range(sliceNodes.GetNumberOfItems()):
                sNode = sliceNodes.GetItemAsObject(i)
                if sNode is not None and hasattr(sNode, "JumpSlice"):
                    sNode.JumpSlice(float(midpoint[0]), float(midpoint[1]), float(midpoint[2]))
            resultado: Result[str] = Ok(f"Vistas ortogonales centradas en trayectoria '{traj.name}'.")
        else:
            resultado = Ok("Recentrado simulado (entorno sin GUI).")

        return resultado

    def exportPlanToFile(
        self,
        trajectories: Sequence[TrajectoryMetrics],
        filepath: str,
        file_format: str = "json",
        coordinate_system: str = "RAS",
        patient_id: str = "ANONYMIZED_PATIENT",
    ) -> Result[str]:
        """Exporta el plan quirúrgico estereotáctico completo a formato JSON, CSV o Slicer Markups JSON."""
        if not trajectories:
            return Err("No hay trayectorias disponibles para exportar.")

        if not filepath:
            return Err("Ruta de archivo no especificada.")

        fmt = file_format.strip().lower()
        if fmt == "json":
            res = export_trajectories_to_json_file(
                trajectories,
                filepath,
                patient_id=patient_id,
                coordinate_system=coordinate_system,
            )
        elif fmt == "csv_summary":
            res = export_trajectories_to_csv_file(
                trajectories,
                filepath,
                coordinate_system=coordinate_system,
                include_contact_rows=False,
            )
        elif fmt in ("csv", "csv_detailed"):
            res = export_trajectories_to_csv_file(
                trajectories,
                filepath,
                coordinate_system=coordinate_system,
                include_contact_rows=True,
            )
        elif fmt in ("markups", "mrk.json"):
            res = export_trajectories_to_slicer_markups_json(
                trajectories,
                filepath,
                coordinate_system=coordinate_system,
            )
        else:
            res = Err(f"Formato de exportación desconocido: '{file_format}'.")

        resultado: Result[str] = res
        return resultado

    def transmitPlanViaOpenIGTLink(
        self,
        trajectories: Sequence[TrajectoryMetrics],
        host: str = "127.0.0.1",
        port: int = 18944,
        timeout_sec: float = 2.0,
        coordinate_system: str = "RAS",
    ) -> Result[Dict[str, int]]:
        """Transmite transformaciones y puntos a un servidor OpenIGTLink sin bloquear la aplicación."""
        if not trajectories:
            return Err("No hay trayectorias disponibles para transmitir por OpenIGTLink.")

        res = transmit_openigtlink_trajectories(
            trajectories,
            host=host,
            port=port,
            timeout_sec=timeout_sec,
            coordinate_system=coordinate_system,
        )
        resultado: Result[Dict[str, int]] = res
        return resultado


class SEEGPlannerTest(ScriptedLoadableModuleTest):
    """Suite de pruebas integrada autoejecutable dentro del entorno interactivo de 3D Slicer."""

    def setUp(self) -> None:
        """Limpia la escena MRML antes de cada test."""
        if slicer and hasattr(slicer, "mrmlScene") and slicer.mrmlScene:
            slicer.mrmlScene.Clear(0)

    def runTest(self) -> None:
        """Ejecuta todos los casos de prueba del módulo."""
        self.setUp()
        self.test_SEEGPlanner1()
        self.test_SEEGPlanner_VolumeAndTargets()
        self.test_SEEGPlanner_SurfaceAnd1020Projection()
        self.test_SEEGPlanner_TrajectoriesAndSafetyCheck()
        self.test_SEEGPlanner_ClinicalDashboardAndUI()
        self.test_SEEGPlanner_ExportAndOpenIGTLink()

    def test_SEEGPlanner1(self) -> None:
        """Prueba de inicialización y trazado básico en la escena MRML de Slicer."""
        self.delayDisplay("Iniciando test de SEEGPlanner...")
        logic = SEEGPlannerLogic()

        # 1. Crear plantilla de referencias
        templateNode = logic.createTemplateLandmarksNode()
        self.assertIsNotNone(templateNode)
        self.assertEqual(templateNode.GetNumberOfControlPoints(), 4)

        # 2. Calcular rejilla 10-20
        gridResult = logic.compute1020Grid(templateNode)
        self.assertIsInstance(gridResult, Ok)
        self.assertIn("Cz", gridResult.value)

        # 3. Validar creación de trayectoria
        entryNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", "TestEntry")
        entryNode.AddControlPoint([40.0, -10.0, 30.0], "Entry")

        targetNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", "TestTarget")
        targetNode.AddControlPoint([20.0, -10.0, -10.0], "Target")

        trajResult = logic.computeTrajectoryBetweenNodes(entryNode, targetNode)
        self.assertIsInstance(trajResult, Ok)
        self.assertGreater(trajResult.value.length_mm, 20.0)

        self.delayDisplay("Test de SEEGPlanner 1 completado con éxito.")

    def test_SEEGPlanner_VolumeAndTargets(self) -> None:
        """Prueba la validación de volúmenes MRI y extracción de dianas desde segmentación MRML."""
        self.delayDisplay("Iniciando test de validación de volúmenes y dianas...")
        logic = SEEGPlannerLogic()

        # 1. Crear volumen sintético
        vol = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", "TestMRI_Vol")
        imgData = vtk.vtkImageData()
        imgData.SetDimensions(64, 64, 64)
        imgData.AllocateScalars(vtk.VTK_SHORT, 1)
        vol.SetAndObserveImageData(imgData)
        vol.SetSpacing(1.0, 1.0, 1.2)

        volRes = logic.validateAndInspectVolume(vol)
        self.assertIsInstance(volRes, Ok)
        self.assertTrue(volRes.value.is_stereotaxy_optimal)

        # 2. Centrado de vistas
        alignRes = logic.alignAndCenterVolume(vol)
        self.assertIsInstance(alignRes, Ok)

        # 3. Crear nodo de segmentación sintético con segmentos
        segNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", "TestBrainSegmentation")
        segmentation = segNode.GetSegmentation()
        segmentation.AddEmptySegment("Hippocampus_Left", "Hippocampus_Left")
        segmentation.AddEmptySegment("Amygdala_Right", "Amygdala_Right")

        targetsRes = logic.extractTargetsFromSegmentation(segNode, vol)
        self.assertIsInstance(targetsRes, Ok)
        self.assertEqual(len(targetsRes.value), 2)

        # Comprobar que se generó el nodo SEEG_Targets
        targetsFid = slicer.mrmlScene.GetFirstNodeByName("SEEG_Targets")
        self.assertIsNotNone(targetsFid)
        self.assertEqual(targetsFid.GetNumberOfControlPoints(), 2)

        self.delayDisplay("Test de SEEGPlanner Volumen y Dianas completado con éxito.")

    def test_SEEGPlanner_SurfaceAnd1020Projection(self) -> None:
        """Prueba la generación de superficie 3D de la cabeza y la proyección de electrodos 10-20."""
        self.delayDisplay("Iniciando test de superficie y proyección 10-20...")
        logic = SEEGPlannerLogic()

        # 1. Crear volumen sintético con esfera de intensidad para representar cabeza
        vol = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", "TestMRI_Head")
        imgData = vtk.vtkImageData()
        imgData.SetDimensions(40, 40, 40)
        imgData.AllocateScalars(vtk.VTK_FLOAT, 1)
        for z in range(40):
            for y in range(40):
                for x in range(40):
                    r_sq = (x - 20) ** 2 + (y - 20) ** 2 + (z - 20) ** 2
                    val = 150.0 if r_sq <= 144 else 0.0
                    imgData.SetScalarComponentFromFloat(x, y, z, 0, val)
        vol.SetAndObserveImageData(imgData)
        vol.SetSpacing(1.0, 1.0, 1.0)
        vol.SetOrigin(-20.0, -20.0, -20.0)

        # 2. Generar superficie 3D de la cabeza
        surfRes = logic.generateHeadSurfaceModel(vol, thresholdRatio=0.2)
        self.assertIsInstance(surfRes, Ok)
        headModel = surfRes.value
        self.assertIsNotNone(headModel)
        self.assertGreater(headModel.GetPolyData().GetNumberOfPoints(), 50)

        # 3. Crear fiduciales de referencia
        templateNode = logic.createTemplateLandmarksNode()

        # 4. Calcular y proyectar rejilla 10-20
        gridRes = logic.compute1020Grid(templateNode, headModelNode=headModel)
        self.assertIsInstance(gridRes, Ok)
        self.assertIn("Cz", gridRes.value)

        gridNode = slicer.mrmlScene.GetFirstNodeByName("EEG_1020_Grid")
        self.assertIsNotNone(gridNode)
        self.assertGreaterEqual(gridNode.GetNumberOfControlPoints(), 20)

        self.delayDisplay("Test de SEEGPlanner Superficie y Proyección completado con éxito.")

    def test_SEEGPlanner_TrajectoriesAndSafetyCheck(self) -> None:
        """Prueba la planificación de trayectorias, modelado 3D tubular y detección de conflictos."""
        self.delayDisplay("Iniciando test de trayectorias y seguridad...")
        logic = SEEGPlannerLogic()

        # 1. Crear fiduciales de entrada y diana para Electrodo 1
        entryFid1 = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", "TestEntry1")
        entryFid1.AddControlPoint([20.0, 30.0, 60.0], "Entry1")
        targetFid1 = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", "TestTarget1")
        targetFid1.AddControlPoint([10.0, 10.0, 10.0], "Target1")

        cfg = ElectrodeConfig(diameter_mm=0.8, num_contacts=8, bolt_length_mm=15.0)
        res1 = logic.computeTrajectoryBetweenNodes(
            entryFid1,
            targetFid1,
            config=cfg,
            renderTube=True,
            electrodeName="Elec_Test_1",
        )
        self.assertIsInstance(res1, Ok)
        m1 = res1.value
        self.assertGreater(m1.length_mm, 30.0)
        self.assertEqual(len(m1.contacts), 8)

        # Verificar que se crearon los nodos en la escena
        lineNode = slicer.mrmlScene.GetFirstNodeByName("Elec_Test_1_Line")
        self.assertIsNotNone(lineNode)
        modelNode = slicer.mrmlScene.GetFirstNodeByName("Elec_Test_1_Model")
        self.assertIsNotNone(modelNode)
        self.assertGreater(modelNode.GetPolyData().GetNumberOfPoints(), 10)

        # 2. Crear Electrodo 2 con entrada a solo 6 mm (conflicto de perno en cráneo)
        entryFid2 = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", "TestEntry2")
        entryFid2.AddControlPoint([26.0, 30.0, 60.0], "Entry2")
        targetFid2 = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", "TestTarget2")
        targetFid2.AddControlPoint([15.0, 20.0, 10.0], "Target2")

        res2 = logic.computeTrajectoryBetweenNodes(
            entryFid2,
            targetFid2,
            config=cfg,
            renderTube=True,
            electrodeName="Elec_Test_2",
        )
        self.assertIsInstance(res2, Ok)
        m2 = res2.value

        # 3. Evaluar conflictos globales
        conflicts_res = logic.checkPlannedConflicts([m1, m2], minEntryDistMm=10.0, minIntracranialDistMm=3.0)
        self.assertIsInstance(conflicts_res, Ok)
        self.assertGreater(len(conflicts_res.value), 0)
        self.assertTrue(any(c.conflict_type == "SKULL_ENTRY_COLLISION" for c in conflicts_res.value))

        self.delayDisplay("Test de SEEGPlanner Trayectorias y Seguridad completado con éxito.")

    def test_SEEGPlanner_ClinicalDashboardAndUI(self) -> None:
        """Prueba el ciclo de vida y gestión limpia de electrodos en el cuadro de mandos clínico."""
        self.delayDisplay("Iniciando test de cuadro de mandos clínico y ciclo de vida MRML...")
        logic = SEEGPlannerLogic()

        entryFid = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", "Entry_Dashboard")
        entryFid.AddControlPoint([15.0, 25.0, 50.0], "Entry")
        targetFid = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", "Target_Dashboard")
        targetFid.AddControlPoint([5.0, 5.0, 5.0], "Target")

        trajs: List[TrajectoryMetrics] = []
        res = logic.computeTrajectoryBetweenNodes(
            entryFid,
            targetFid,
            electrodeName="Elec_Dash_Test",
            renderTube=True,
        )
        self.assertIsInstance(res, Ok)
        trajs.append(res.value)

        # Verificar existencia inicial de nodos
        self.assertIsNotNone(slicer.mrmlScene.GetFirstNodeByName("Elec_Dash_Test_Line"))
        self.assertIsNotNone(slicer.mrmlScene.GetFirstNodeByName("Elec_Dash_Test_Model"))

        # Recentrado
        focus_res = logic.focusTrajectoryInViews(trajs[0])
        self.assertIsInstance(focus_res, Ok)

        # Eliminación sincronizada y verificación de ausencia de nodos huérfanos
        remove_res = logic.removePlannedTrajectoryByIndex(0, trajs)
        self.assertIsInstance(remove_res, Ok)
        self.assertEqual(len(trajs), 0)
        self.assertIsNone(slicer.mrmlScene.GetFirstNodeByName("Elec_Dash_Test_Line"))
        self.assertIsNone(slicer.mrmlScene.GetFirstNodeByName("Elec_Dash_Test_Model"))

        self.delayDisplay("Test de Cuadro de Mandos y Ciclo de Vida MRML completado con éxito.")

    def test_SEEGPlanner_ExportAndOpenIGTLink(self) -> None:
        """Prueba la exportación a formatos abiertos (JSON, CSV, Markups) y la integración OpenIGTLink."""
        import tempfile
        self.delayDisplay("Iniciando test de exportación y OpenIGTLink...")
        logic = SEEGPlannerLogic()

        entryFid = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", "Export_Entry")
        entryFid.AddControlPoint([20.0, 30.0, 50.0], "Entry")
        targetFid = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", "Export_Target")
        targetFid.AddControlPoint([5.0, 10.0, 5.0], "Target")

        cfg = ElectrodeConfig(diameter_mm=0.8, num_contacts=8)
        traj_res = logic.computeTrajectoryBetweenNodes(
            entryFid,
            targetFid,
            electrodeName="Elec_Export_Test",
            config=cfg,
        )
        self.assertIsInstance(traj_res, Ok)
        trajs = [traj_res.value]

        tmp_dir = tempfile.mkdtemp()
        try:
            # 1. Exportación JSON
            json_file = os.path.join(tmp_dir, "plan.json")
            res_json = logic.exportPlanToFile(trajs, json_file, file_format="json", coordinate_system="RAS")
            self.assertIsInstance(res_json, Ok)
            self.assertTrue(os.path.exists(json_file))

            # 2. Exportación CSV
            csv_file = os.path.join(tmp_dir, "plan.csv")
            res_csv = logic.exportPlanToFile(trajs, csv_file, file_format="csv_detailed", coordinate_system="LPS")
            self.assertIsInstance(res_csv, Ok)
            self.assertTrue(os.path.exists(csv_file))

            # 3. Exportación Slicer Markups JSON
            mrk_file = os.path.join(tmp_dir, "plan.mrk.json")
            res_mrk = logic.exportPlanToFile(trajs, mrk_file, file_format="markups", coordinate_system="RAS")
            self.assertIsInstance(res_mrk, Ok)
            self.assertTrue(os.path.exists(mrk_file))

            # 4. Transmisión OpenIGTLink con timeout corto (puerto cerrado defensivo)
            res_net = logic.transmitPlanViaOpenIGTLink(trajs, host="127.0.0.1", port=59998, timeout_sec=0.2)
            self.assertIsInstance(res_net, Err)
        finally:
            for root, dirs, files in os.walk(tmp_dir, topdown=False):
                for f in files:
                    try:
                        os.remove(os.path.join(root, f))
                    except OSError:
                        pass
                for d in dirs:
                    try:
                        os.rmdir(os.path.join(root, d))
                    except OSError:
                        pass
            try:
                os.rmdir(tmp_dir)
            except OSError:
                pass

        self.delayDisplay("Test de SEEGPlanner Exportación y OpenIGTLink completado con éxito.")
