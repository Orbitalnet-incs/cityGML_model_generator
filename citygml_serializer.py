import os
from typing import List, Union

from qgis.PyQt.QtXml import QDomDocument, QDomNode, QDomElement
from qgis.PyQt.QtCore import QFile, QTextStream

from qgis.core import *

from .basedata_read import BasedataRead

class CityGMLSerializer:
    def __init__(self, generator: BasedataRead, feature_type: str, output_dir_path: str):
        self.__output_dir_path = output_dir_path

        self.generator = generator
        self.feature_type = feature_type

        if feature_type == "bldg:Building":
            # 建築物
            self.__document_factory = CityGMLBuildingDocumentFactory()

        # elif feature_type == "bldg:BuildingPart":
        #     # 建築物部分
        #     self.__document_factory = CityGMLBuildingPartDocumentFactory()

        elif feature_type == "luse:LandUse":
            # 土地利用
            self.__document_factory = CityGMLLandUseDocumentFactory()

        elif feature_type == "tran:Road":
            # 道路
            self.__document_factory = CityGMLRoadDocumentFactory()

        elif feature_type == "dem:ReliefFeature":
            # 地形（起伏）
            self.__document_factory = CityGMLReliefFeatureDocumentFactory()

        # elif feature_type == "dem:TinRelief":
        #     # TIN
        #     self.__document_factory = CityGMLTinReliefDocumentFactory()

        # elif feature_type == "wtr:WaterBody":
        #     # 洪水浸水想定区域、津波浸水想定
        #     self.__document_factory = CityGMLWaterBodyDocumentFactory()

        else:
            self.__document_factory = None

    def outputDirPath(self) -> str:
        return self.__output_dir_path

    def setOutputDirPath(self, path: str):
        self.__output_dir_path = path

    def exec(self, feature_itr: QgsFeatureIterator, boundedBy, meshcode: str) -> str:
        """実行"""

        if self.__document_factory is None:
            return None

        file_name = f"{meshcode}_{self.__document_factory.prefix()}_6697.gml"

        # idと高さフィールド名の設定
        self.__document_factory.boundedBy= boundedBy
        self.__document_factory.setGmlIdFieldName(self.generator.requiredField())
        self.__document_factory.setHeightFieldName(self.generator.heightFeatureField())
        
        doc = self.__document_factory.createDocument(feature_itr)
        if doc is None:
            return None

        # 既存ファイルがあっても上書きする
        output_path = os.path.join(self.__output_dir_path, file_name)
        f = QFile(output_path)
        if f.open(QFile.WriteOnly | QFile.Text) == False:
            return None

        text_stream = QTextStream(f)
        text_stream.setCodec("UTF-8")

        doc.save(text_stream, 2, QDomNode.EncodingFromTextStream)

        f.close()

        return file_name

    def lastError(self):
        return self.lastError

class CityGMLDocumentFactory:
    """DomDocumentファクトリー親クラス"""
    def __init__(self):
        self.root_tag_name = "core:CityModel"

        self.boundedBy = None # gml:boundedByの数値
        self.__gml_id_field_name = "gml_id"
        self.__height_field_name = "height"


    def gmlIdFieldName(self) -> str:
        return self.__gml_id_field_name

    def setGmlIdFieldName(self, field_name: str):
        self.__gml_id_field_name = field_name

    def heightFieldName(self) -> str:
        return self.__height_field_name

    def setHeightFieldName(self, field_name: str):
        self.__height_field_name = field_name

    def createDocument(self, feature_itr: QgsFeatureIterator) -> QDomDocument:
        """DomDocument生成処理"""
        doc = QDomDocument()
        el_decl = doc.createProcessingInstruction('xml', 'version="1.0" encoding="utf-8"')
        doc.appendChild(el_decl)

        el_city_model = doc.createElement(self.root_tag_name)
        el_city_model.setAttribute("xmlns:uro","http://www.kantei.go.jp/jp/singi/tiiki/toshisaisei/itoshisaisei/iur/uro/1.1")
        el_city_model.setAttribute("xmlns:core","http://www.opengis.net/citygml/2.0")
        el_city_model.setAttribute("xmlns:bldg","http://www.opengis.net/citygml/building/2.0")
        el_city_model.setAttribute("xmlns:gen","http://www.opengis.net/citygml/generics/2.0")
        el_city_model.setAttribute("xmlns:luse","http://www.opengis.net/citygml/landuse/2.0")
        el_city_model.setAttribute("xmlns:dem","http://www.opengis.net/citygml/relief/2.0")
        el_city_model.setAttribute("xmlns:tran","http://www.opengis.net/citygml/transportation/2.0")
        el_city_model.setAttribute("xmlns:wtr","http://www.opengis.net/citygml/waterbody/2.0")
        el_city_model.setAttribute("xmlns:gml","http://www.opengis.net/gml")
        el_city_model.setAttribute("xmlns:xAL","urn:oasis:names:tc:ciq:xsdschema:xAL:2.0")
        el_city_model.setAttribute("xmlns:sch","http://www.ascc.net/xml/schematron")
        doc.appendChild(el_city_model)

        el_bounded_by = doc.createElement("gml:boundedBy")
        el_city_model.appendChild(el_bounded_by)

        el_envelope = doc.createElement("gml:Envelope")
        el_envelope.setAttribute("srsName", "http://www.opengis.net/def/crs/EPSG/0/6697")
        el_bounded_by.appendChild(el_envelope)

        el_lower_corner = doc.createElement("gml:lowerCorner")
        el_lower_corner.setAttribute("srsDimension", '3')
        tx_loser_corner = doc.createTextNode(self.boundedBy[0] + " " + self.boundedBy[1] + " 0.0")
        el_lower_corner.appendChild(tx_loser_corner)
        el_envelope.appendChild(el_lower_corner)

        el_upper_corner = doc.createElement("gml:upperCorner")
        el_upper_corner.setAttribute("srsDimension", '3')
        tx_upper_corner = doc.createTextNode(self.boundedBy[2] + " " + self.boundedBy[3] + " 0.0")
        el_upper_corner.appendChild(tx_upper_corner)
        el_envelope.appendChild(el_upper_corner)

        # 地物ごとに要素cityObjectMemberを生成する
        for feature in feature_itr:
            # タグ名とid
            el_member = doc.createElement(self.tagName())
            try:
                gml_id = feature.attribute(self.gmlIdFieldName())
            except KeyError:
                # なければフィーチャーID
                gml_id = feature.id()

            el_member.setAttribute("gml:id", gml_id)

            # 属性設定
            # 開発中

            # 地物全体の高さ取得
            measured_height = None
            try:
                if self.heightFieldName() != None and self.heightFieldName() != "":
                    measured_height = feature.attribute(self.heightFieldName())
            except KeyError:
                pass

            # 各種要素の生成
            el_geometries = self.makeGeometryElements(feature.geometry(), measured_height, doc)
            for el_geometry in el_geometries:
                if el_geometry is not None:
                    el_member.appendChild(el_geometry)

            if el_member is not None:
                el_city_object_member = doc.createElement("core:cityObjectMember")
                el_city_model.appendChild(el_city_object_member)
                el_city_object_member.appendChild(el_member)

        return doc

    def tagName(self) -> str:
        return ""

    def prefix(self) -> str:
        return ""

    def makeGeometryElements(self, geometry: QgsGeometry, measured_height: float, doc: QDomDocument) -> List[QDomElement]:
        # インターフェース
        pass


class CityGMLBuildingDocumentFactory(CityGMLDocumentFactory):
    """建築物DomDocumentファクトリークラス"""

    def tagName(self):
        return "bldg:Building"

    def prefix(self):
        return "bldg"

    def makeGeometryElements(self, geometry: QgsGeometry, measured_height, doc: QDomDocument) -> List[QDomElement]:
        # bldg:lod0FootPrint
        el_lod0_foot_print = doc.createElement("bldg:lod0FootPrint")
        el_lod0_foot_print.appendChild(makeMultiSurface(geometry, doc))

        # bldg:measuredHeight
        el_measuredHeight = None
        if measured_height != None:
            el_measuredHeight = doc.createElement("bldg:measuredHeight")
            el_measuredHeight.setAttribute("uom", "m")
            el_measuredHeight.appendChild(doc.createTextNode(str(measured_height)))

        # bldg:lod0RoofEdge
        el_lod0_roof_edge = doc.createElement("bldg:lod0RoofEdge")
        el_lod0_roof_edge.appendChild(makeMultiSurface(geometry, doc))

        # bldg:lod1Solid
        el_lod1_solid = doc.createElement("bldg:lod1Solid")
        el_lod1_solid.appendChild(makeSolid(geometry, doc))

        return [el_lod0_foot_print, el_measuredHeight, el_lod0_roof_edge, el_lod1_solid]


# class CityGMLBuildingPartDocumentFactory(CityGMLBuildingDocumentFactory):
#     """建築物部分DomDocumentファクトリークラス"""
#     def __init__(self):
#         super().__init__()

#     def tagName(self):
#         return "bldg:BuildingPart"

class CityGMLLandUseDocumentFactory(CityGMLDocumentFactory):
    """土地利用DomDocumentファクトリークラス"""
    def __init__(self):
        super().__init__()
        self.__builder = None

    def tagName(self):
        return "luse:LandUse"

    def prefix(self):
        return "luse"

    def makeGeometryElements(self, geometry: QgsGeometry, height: float, doc: QDomDocument) -> List[QDomElement]:
        el_lod1_multi_surface = doc.createElement("use:lod1MultiSurface")
        el_lod1_multi_surface.appendChild(makeMultiSurface(geometry, doc))

        return [el_lod1_multi_surface]

class CityGMLRoadDocumentFactory(CityGMLDocumentFactory):
    """道路DomDocumentファクトリークラス"""
    def __init__(self):
        super().__init__()
        self.__builder = None

    def tagName(self):
        return "tran:Road"

    def prefix(self):
        return "tran"

    def makeGeometryElements(self, geometry: QgsGeometry, height: float, doc: QDomDocument) -> List[QDomElement]:
        el_lod1_multi_surface = doc.createElement("tran:lod1MultiSurface")
        el_lod1_multi_surface.appendChild(makeMultiSurface(geometry, doc))

        return [el_lod1_multi_surface]

class CityGMLReliefFeatureDocumentFactory(CityGMLDocumentFactory):
    """地形（起伏）DomDocumentファクトリークラス"""
    def __init__(self):
        super().__init__()
        self.__builder = None

    def tagName(self):
        return "dem:ReliefFeature"

    def prefix(self):
        return "dem"

    def makeGeometryElements(self, geometry: QgsGeometry, height: float, doc: QDomDocument) -> List[QDomElement]:
        el_lod1_multi_surface = doc.createElement("dem:lod")
        el_lod1_multi_surface.appendChild(makeMultiSurface(geometry, doc))
        return [el_lod1_multi_surface]

# class CityGMLTinReliefDocumentFactory(CityGMLDocumentFactory):
#     """TINDomDocumentファクトリークラス"""
#     def __init__(self):
#         super().__init__()
#         self.__builder = None

#     def tagName(self):
#         return "dem:TinRelief"

#     def prefix(self):
#         return "dem"

#     def makeGeometryElements(self, geometry: QgsGeometry, height: float, doc: QDomDocument) -> List[QDomElement]:
#         el_lod1_multi_surface = doc.createElement("use:lod1MultiSurface")
#         el_lod1_multi_surface.appendChild(makeMultiSurface(geometry, doc))

#         return [el_lod1_multi_surface]

# class CityGMLWaterBodyDocumentFactory(CityGMLDocumentFactory):
#     """洪水浸水想定区域、津波浸水想定DomDocumentファクトリークラス"""
#     def __init__(self):
#         super().__init__()
#         self.__builder = None

#     def tagName(self):
#         return "wtr:WaterBody"

#     def prefix(self):
#         return "wtr"

#     def makeGeometryElements(self, geometry: QgsGeometry, height: float, doc: QDomDocument) -> List[QDomElement]:
#         el_lod1_multi_surface = doc.createElement("wtr:lod1MultiSurface")
#         el_lod1_multi_surface.appendChild(makeMultiSurface(geometry, doc))
#         return [el_lod1_multi_surface]
        
def makeMultiSurface(geom: QgsGeometry, doc: QDomDocument) -> QDomElement:
    """ 要素MultiSurfaceを生成する """
    el_multi_surface = doc.createElement("gml:MultiSurface")

    el_surface_member = doc.createElement("gml:surfaceMember")
    el_multi_surface.appendChild(el_surface_member)

    el_polygon = doc.createElement("gml:Polygon")
    el_surface_member.appendChild(el_polygon)

    part_index = 0
    for part in geom.parts():
        element_name = "gml:exterior" if part_index == 0 else "gml:interior"
        el_element = doc.createElement(element_name)
        el_polygon.appendChild(el_element)

        el_linear_ring = doc.createElement("gml:LinearRing")
        el_element.appendChild(el_linear_ring)

        vertices = []
        for v in part.vertices():
            vertices.append(v.clone())

        # el_point_list = makePosList(vertices, feat_height, doc)
        el_point_list = makePosList(vertices, doc)
        el_linear_ring.appendChild(el_point_list)

    return el_multi_surface


def makePosList(vertices: List[Union[QgsPoint, QgsPointXY]], doc: QDomDocument) -> QDomElement:
    """ 要素posListを生成する """
    points = []
    for vertex in vertices:
        # 緯度、経度の順
        points.append(f"{vertex.y()}")
        points.append(f"{vertex.x()}")

        # 標高
        if vertex.z() != None and f"{vertex.z()}" != "nan":
            points.append(f"{vertex.z()}")
        else:
            points.append("0.0")

    el_pos_list = doc.createElement("gml:posList")
    el_pos_list.appendChild(doc.createTextNode(" ".join(points)))

    return el_pos_list

def makeSolid(geom: QgsGeometry, doc: QDomDocument) -> QDomElement:
    """ 要素Solidを生成する """
    el_solid = doc.createElement("gml:Solid")
    for part in geom.parts():
        el_exterior = doc.createElement("gml:exterior")
        el_solid.appendChild(el_exterior)

        el_composite_surface = doc.createElement("gml:CompositeSurface")
        el_exterior.appendChild(el_composite_surface)

        # 個体
        vertices = []
        for vertex in part.vertices():
            if len(vertices) > 0:
                # 各線分に対して側面を作成する
                el_surface_member = doc.createElement("gml:surfaceMember")
                el_composite_surface.appendChild(el_surface_member)

                el_surface_member.appendChild(makeSidePolygon(vertices[-1], vertex, doc))

            vertices.append(vertex.clone())

        # 底面(el_composite_surface配下)
        last_polygon = makeBottomSurface(vertices, doc)
        el_composite_surface.appendChild(last_polygon)

        # exteriorのみ
        break


    return el_solid

def makeSidePolygon(start: Union[QgsPointXY, QgsPoint], end: Union[QgsPointXY, QgsPoint], doc: QDomDocument) -> QDomElement:
    """ 側面の要素Polygonを生成する """

    el_polygon = doc.createElement("gml:Polygon")

    el_exterior = doc.createElement("gml:exterior")
    el_polygon.appendChild(el_exterior)

    el_linear_ring = doc.createElement("gml:LinearRing")
    el_exterior.appendChild(el_linear_ring)

    pos_list = []
    # 左回り
    # 座標値の並びは緯度、経度、標高

    # 底辺
    pos_list.append(f"{start.y()}")
    pos_list.append(f"{start.x()}")
    pos_list.append("0.0")

    pos_list.append(f"{end.y()}")
    pos_list.append(f"{end.x()}")
    pos_list.append("0.0")

    # 左辺
    pos_list.append(f"{end.y()}")
    pos_list.append(f"{end.x()}")
    if end.z() != None and f"{end.z()}" != "nan":
        pos_list.append(f"{end.z()}")
    else:
        pos_list.append("0.0")

    # 上辺
    pos_list.append(f"{start.y()}")
    pos_list.append(f"{start.x()}")
    if start.z() != None and f"{start.z()}" != "nan":
        pos_list.append(f"{start.z()}")
    else:
        pos_list.append("0.0")

    # 右辺
    pos_list.append(f"{start.y()}")
    pos_list.append(f"{start.x()}")
    pos_list.append("0.0")

    el_pos_list = doc.createElement("gml:posList")
    el_pos_list.appendChild(doc.createTextNode(" ".join(pos_list)))
    el_linear_ring.appendChild(el_pos_list)

    return el_polygon


def makeBottomSurface(vertices: List[Union[QgsPoint, QgsPointXY]], doc: QDomDocument) -> QDomElement:
    """ 底面の要素surfaceMemberを生成する """    
    el_surface_member = doc.createElement("gml:surfaceMember")
    el_polygon = doc.createElement("gml:Polygon")
    el_exterior = doc.createElement("gml:exterior")
    el_polygon.appendChild(el_exterior)
    el_linear_ring = doc.createElement("gml:LinearRing")
    el_exterior.appendChild(el_linear_ring)
    el_pos_list = makePosList(vertices, doc)
    el_linear_ring.appendChild(el_pos_list)
    el_surface_member.appendChild(el_polygon)

    return el_surface_member