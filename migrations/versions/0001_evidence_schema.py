"""Create the four evidence-owned tables from the monolith schema."""
from alembic import op

revision = "0001_evidence_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE TABLE `incidencias` (\n  `id` CHAR(36) NOT NULL,\n  `prestamo_id` CHAR(36) NOT NULL,\n  `reportada_por_usuario_id` CHAR(36) NOT NULL,\n  `tipo` VARCHAR(24) NOT NULL,\n  `descripcion` TEXT NOT NULL,\n  `estado` VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE',\n  `reportada_en` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),\n  `revision_iniciada_en` DATETIME(6),\n  `resuelta_en` DATETIME(6),\n  `resuelta_por_usuario_id` CHAR(36),\n  `justificacion_resolucion` TEXT,\n  `decision_garantia` VARCHAR(24),\n  `monto_garantia_afectado` DECIMAL(12,2),\n  `saldo_garantia_previsto` DECIMAL(12,2),\n  `moneda` CHAR(3),\n  `actualizada_en` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),\n  PRIMARY KEY (`id`),\n  KEY `idx_incidencias_0` (`estado`, `tipo`, `reportada_en`),\n  KEY `idx_incidencias_1` (`prestamo_id`, `estado`)\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4")
    op.execute("CREATE TABLE `evidencias` (\n  `id` CHAR(36) NOT NULL,\n  `prestamo_id` CHAR(36) NOT NULL,\n  `incidencia_id` CHAR(36),\n  `registrada_por_usuario_id` CHAR(36) NOT NULL,\n  `etapa` VARCHAR(20) NOT NULL,\n  `tipo` VARCHAR(20) NOT NULL,\n  `url` TEXT,\n  `cloudinary_public_id` VARCHAR(255),\n  `observacion` TEXT,\n  `registrada_en` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),\n  `estado_integracion` VARCHAR(24) NOT NULL DEFAULT 'PENDIENTE',\n  PRIMARY KEY (`id`),\n  KEY `idx_evidencias_0` (`prestamo_id`, `etapa`, `registrada_en`),\n  KEY `idx_evidencias_1` (`incidencia_id`),\n  CONSTRAINT `fk_evidencias_incidencia_id` FOREIGN KEY (`incidencia_id`) REFERENCES `incidencias` (`id`) ON DELETE RESTRICT\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4")
    op.execute("CREATE TABLE `analisis_evidencias` (\n  `id` CHAR(36) NOT NULL,\n  `prestamo_id` CHAR(36) NOT NULL,\n  `incidencia_id` CHAR(36),\n  `evidencia_inicial_id` CHAR(36) NOT NULL,\n  `evidencia_final_id` CHAR(36) NOT NULL,\n  `solicitado_por_usuario_id` CHAR(36) NOT NULL,\n  `estado` VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE',\n  `solicitado_en` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),\n  `completado_en` DATETIME(6),\n  `resultado_resumen` TEXT,\n  `resultado_detalle` JSON,\n  `error_descripcion` TEXT,\n  PRIMARY KEY (`id`),\n  KEY `idx_analisis_evidencias_0` (`prestamo_id`, `solicitado_en`),\n  KEY `idx_analisis_evidencias_1` (`incidencia_id`),\n  CONSTRAINT `fk_analisis_evidencias_incidencia_id` FOREIGN KEY (`incidencia_id`) REFERENCES `incidencias` (`id`) ON DELETE RESTRICT,\n  CONSTRAINT `fk_analisis_evidencias_evidencia_inicial_id` FOREIGN KEY (`evidencia_inicial_id`) REFERENCES `evidencias` (`id`) ON DELETE RESTRICT,\n  CONSTRAINT `fk_analisis_evidencias_evidencia_final_id` FOREIGN KEY (`evidencia_final_id`) REFERENCES `evidencias` (`id`) ON DELETE RESTRICT\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4")
    op.execute("CREATE TABLE `observaciones_incidencia` (\n  `id` CHAR(36) NOT NULL,\n  `incidencia_id` CHAR(36) NOT NULL,\n  `administrador_usuario_id` CHAR(36) NOT NULL,\n  `contenido` TEXT NOT NULL,\n  `registrada_en` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),\n  PRIMARY KEY (`id`),\n  KEY `idx_observaciones_incidencia_0` (`incidencia_id`, `registrada_en`),\n  CONSTRAINT `fk_observaciones_incidencia_incidencia_id` FOREIGN KEY (`incidencia_id`) REFERENCES `incidencias` (`id`) ON DELETE RESTRICT\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4")


def downgrade():
    for name in ("observaciones_incidencia", "analisis_evidencias", "evidencias", "incidencias"):
        op.drop_table(name)
