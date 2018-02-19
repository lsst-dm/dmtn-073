+----------------------+----------+-------------+------------------------------------------------------+
| Name                 | Type     | Attributes  | Description                                          |
+======================+==========+=============+======================================================+
| dataset_id           | int      | PRIMARY KEY | | A unique autoincrement field used as part of the   |
|                      |          |             | | primary key for Dataset.                           |
+----------------------+----------+-------------+------------------------------------------------------+
| registry_id          | int      | PRIMARY KEY | | A different number for each potentially            |
|                      |          |             | | independent producer of dataset_ids, used as part  |
|                      |          |             | | of the primary key for Dataset to avoid clashes.   |
+----------------------+----------+-------------+------------------------------------------------------+
| dataset_type_name    | string   | NOT NULL    | | The name of the DatasetType associated with this   |
|                      |          |             | | Dataset; a reference to the DatasetType table.     |
+----------------------+----------+-------------+------------------------------------------------------+
| run_id               | int      | NOT NULL    | | The ID of the Run that produced this Dataset,      |
|                      |          |             | | providing access to coarse provenance information. |
|                      |          |             | | The registry_id of the associated Run is assumed   |
|                      |          |             | | to be the same as that of the Dataset itself.      |
+----------------------+----------+-------------+------------------------------------------------------+
| quantum_id           | int      |             | | The ID of the Quantum that produced this Dataset,  |
|                      |          |             | | providing access to fine-grained provenance        |
|                      |          |             | | information.  The registry_id of the associated    |
|                      |          |             | | Quantum is assumed to be the same as that of the   |
|                      |          |             | | Dataset itself.  May be null for Datasets not      |
|                      |          |             | | produced by running a SuperTask.                   |
+----------------------+----------+-------------+------------------------------------------------------+
| label                | string   |             | | DataUnit link; see Label.                          |
+----------------------+----------+-------------+------------------------------------------------------+
| skymap               | string   |             | | DataUnit link; see SkyMap.                         |
+----------------------+----------+-------------+------------------------------------------------------+
| tract                | int      |             | | DataUnit link; see Tract.                          |
+----------------------+----------+-------------+------------------------------------------------------+
| patch                | int      |             | | DataUnit link; see Patch.                          |
+----------------------+----------+-------------+------------------------------------------------------+
| skypix               | int      |             | | DataUnit link; see SkyPix.                         |
+----------------------+----------+-------------+------------------------------------------------------+
| camera               | string   |             | | DataUnit link; see Camera.                         |
+----------------------+----------+-------------+------------------------------------------------------+
| valid_first          | int      |             | | DataUnit link; see ExposureRange.                  |
+----------------------+----------+-------------+------------------------------------------------------+
| valid_last           | int      |             | | DataUnit link; see ExposureRange.                  |
+----------------------+----------+-------------+------------------------------------------------------+
| abstract_filter      | string   |             | | DataUnit link; see AbstractFilter.                 |
+----------------------+----------+-------------+------------------------------------------------------+
| physical_filter      | string   |             | | DataUnit link; see PhysicalFilter.                 |
+----------------------+----------+-------------+------------------------------------------------------+
| visit                | int      |             | | DataUnit link; see Visit.                          |
+----------------------+----------+-------------+------------------------------------------------------+
| exposure             | int      |             | | DataUnit link; see Exposure.                       |
+----------------------+----------+-------------+------------------------------------------------------+
| sensor               | string   |             | | DataUnit link; see Sensor.                         |
+----------------------+----------+-------------+------------------------------------------------------+
| FOREIGN KEY (dataset_type_name) REFERENCES DatasetType (dataset_type_name)                           |
+----------------------+----------+-------------+------------------------------------------------------+
| FOREIGN KEY (run_id, registry_id) REFERENCES Run (run_id, registry_id)                               |
+----------------------+----------+-------------+------------------------------------------------------+
| FOREIGN KEY (quantum_id, registry_id) REFERENCES Quantum (quantum_id, registry_id)                   |
+----------------------+----------+-------------+------------------------------------------------------+
| FOREIGN KEY (skymap) REFERENCES SkyMap (skymap)                                                      |
+----------------------+----------+-------------+------------------------------------------------------+
| FOREIGN KEY (skymap, tract) REFERENCES Tract (skymap, tract)                                         |
+----------------------+----------+-------------+------------------------------------------------------+
| FOREIGN KEY (skymap, skymap, tract, patch) REFERENCES Patch (skymap, skymap, tract, patch)           |
+----------------------+----------+-------------+------------------------------------------------------+
| FOREIGN KEY (camera) REFERENCES Camera (camera)                                                      |
+----------------------+----------+-------------+------------------------------------------------------+
| FOREIGN KEY (abstract_filter) REFERENCES AbstractFilter (abstract_filter)                            |
+----------------------+----------+-------------+------------------------------------------------------+
| FOREIGN KEY (camera, physical_filter) REFERENCES PhysicalFilter (camera, physical_filter)            |
+----------------------+----------+-------------+------------------------------------------------------+
| FOREIGN KEY (camera, visit) REFERENCES Visit (camera, visit)                                         |
+----------------------+----------+-------------+------------------------------------------------------+
| FOREIGN KEY (camera, exposure) REFERENCES Exposure (camera, exposure)                                |
+----------------------+----------+-------------+------------------------------------------------------+
| FOREIGN KEY (camera, sensor) REFERENCES Sensor (camera, sensor)                                      |
+----------------------+----------+-------------+------------------------------------------------------+
+----------------------+----------+-------------+------------------------------------------------------+
