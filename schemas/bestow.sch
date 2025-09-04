<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<xsl:stylesheet xmlns:dcr="http://www.isocat.org/ns/dcr"
                xmlns:iso="http://purl.oclc.org/dsdl/schematron"
                xmlns:rng="http://relaxng.org/ns/structure/1.0"
                xmlns:saxon="http://saxon.sf.net/"
                xmlns:schold="http://www.ascc.net/xml/schematron"
                xmlns:tei="http://www.tei-c.org/ns/1.0"
                xmlns:xhtml="http://www.w3.org/1999/xhtml"
                xmlns:xs="http://www.w3.org/2001/XMLSchema"
                xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                version="2.0"><!--Implementers: please note that overriding process-prolog or process-root is 
    the preferred method for meta-stylesheets to use where possible. -->
   <xsl:param name="archiveDirParameter"/>
   <xsl:param name="archiveNameParameter"/>
   <xsl:param name="fileNameParameter"/>
   <xsl:param name="fileDirParameter"/>
   <xsl:variable name="document-uri">
      <xsl:value-of select="document-uri(/)"/>
   </xsl:variable>
   <!--PHASES-->

   <!--PROLOG-->
   <xsl:output xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
               method="xml"
               omit-xml-declaration="no"
               standalone="yes"
               indent="yes"/>
   <!--XSD TYPES FOR XSLT2-->

   <!--KEYS AND FUNCTIONS-->

   <!--DEFAULT RULES-->

   <!--MODE: SCHEMATRON-SELECT-FULL-PATH-->
   <!--This mode can be used to generate an ugly though full XPath for locators-->
   <xsl:template match="*" mode="schematron-select-full-path">
      <xsl:apply-templates select="." mode="schematron-get-full-path"/>
   </xsl:template>
   <!--MODE: SCHEMATRON-FULL-PATH-->
   <!--This mode can be used to generate an ugly though full XPath for locators-->
   <xsl:template match="*" mode="schematron-get-full-path">
      <xsl:apply-templates select="parent::*" mode="schematron-get-full-path"/>
      <xsl:text>/</xsl:text>
      <xsl:choose>
         <xsl:when test="namespace-uri()=''">
            <xsl:value-of select="name()"/>
         </xsl:when>
         <xsl:otherwise>
            <xsl:text>*:</xsl:text>
            <xsl:value-of select="local-name()"/>
            <xsl:text>[namespace-uri()='</xsl:text>
            <xsl:value-of select="namespace-uri()"/>
            <xsl:text>']</xsl:text>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:variable name="preceding"
                    select="count(preceding-sibling::*[local-name()=local-name(current())                                   and namespace-uri() = namespace-uri(current())])"/>
      <xsl:text>[</xsl:text>
      <xsl:value-of select="1+ $preceding"/>
      <xsl:text>]</xsl:text>
   </xsl:template>
   <xsl:template match="@*" mode="schematron-get-full-path">
      <xsl:apply-templates select="parent::*" mode="schematron-get-full-path"/>
      <xsl:text>/</xsl:text>
      <xsl:choose>
         <xsl:when test="namespace-uri()=''">@<xsl:value-of select="name()"/>
         </xsl:when>
         <xsl:otherwise>
            <xsl:text>@*[local-name()='</xsl:text>
            <xsl:value-of select="local-name()"/>
            <xsl:text>' and namespace-uri()='</xsl:text>
            <xsl:value-of select="namespace-uri()"/>
            <xsl:text>']</xsl:text>
         </xsl:otherwise>
      </xsl:choose>
   </xsl:template>
   <!--MODE: SCHEMATRON-FULL-PATH-2-->
   <!--This mode can be used to generate prefixed XPath for humans-->
   <xsl:template match="node() | @*" mode="schematron-get-full-path-2">
      <xsl:for-each select="ancestor-or-self::*">
         <xsl:text>/</xsl:text>
         <xsl:value-of select="name(.)"/>
         <xsl:if test="preceding-sibling::*[name(.)=name(current())]">
            <xsl:text>[</xsl:text>
            <xsl:value-of select="count(preceding-sibling::*[name(.)=name(current())])+1"/>
            <xsl:text>]</xsl:text>
         </xsl:if>
      </xsl:for-each>
      <xsl:if test="not(self::*)">
         <xsl:text/>/@<xsl:value-of select="name(.)"/>
      </xsl:if>
   </xsl:template>
   <!--MODE: SCHEMATRON-FULL-PATH-3-->
   <!--This mode can be used to generate prefixed XPath for humans 
	(Top-level element has index)-->
   <xsl:template match="node() | @*" mode="schematron-get-full-path-3">
      <xsl:for-each select="ancestor-or-self::*">
         <xsl:text>/</xsl:text>
         <xsl:value-of select="name(.)"/>
         <xsl:if test="parent::*">
            <xsl:text>[</xsl:text>
            <xsl:value-of select="count(preceding-sibling::*[name(.)=name(current())])+1"/>
            <xsl:text>]</xsl:text>
         </xsl:if>
      </xsl:for-each>
      <xsl:if test="not(self::*)">
         <xsl:text/>/@<xsl:value-of select="name(.)"/>
      </xsl:if>
   </xsl:template>
   <!--MODE: GENERATE-ID-FROM-PATH -->
   <xsl:template match="/" mode="generate-id-from-path"/>
   <xsl:template match="text()" mode="generate-id-from-path">
      <xsl:apply-templates select="parent::*" mode="generate-id-from-path"/>
      <xsl:value-of select="concat('.text-', 1+count(preceding-sibling::text()), '-')"/>
   </xsl:template>
   <xsl:template match="comment()" mode="generate-id-from-path">
      <xsl:apply-templates select="parent::*" mode="generate-id-from-path"/>
      <xsl:value-of select="concat('.comment-', 1+count(preceding-sibling::comment()), '-')"/>
   </xsl:template>
   <xsl:template match="processing-instruction()" mode="generate-id-from-path">
      <xsl:apply-templates select="parent::*" mode="generate-id-from-path"/>
      <xsl:value-of select="concat('.processing-instruction-', 1+count(preceding-sibling::processing-instruction()), '-')"/>
   </xsl:template>
   <xsl:template match="@*" mode="generate-id-from-path">
      <xsl:apply-templates select="parent::*" mode="generate-id-from-path"/>
      <xsl:value-of select="concat('.@', name())"/>
   </xsl:template>
   <xsl:template match="*" mode="generate-id-from-path" priority="-0.5">
      <xsl:apply-templates select="parent::*" mode="generate-id-from-path"/>
      <xsl:text>.</xsl:text>
      <xsl:value-of select="concat('.',name(),'-',1+count(preceding-sibling::*[name()=name(current())]),'-')"/>
   </xsl:template>
   <!--MODE: GENERATE-ID-2 -->
   <xsl:template match="/" mode="generate-id-2">U</xsl:template>
   <xsl:template match="*" mode="generate-id-2" priority="2">
      <xsl:text>U</xsl:text>
      <xsl:number level="multiple" count="*"/>
   </xsl:template>
   <xsl:template match="node()" mode="generate-id-2">
      <xsl:text>U.</xsl:text>
      <xsl:number level="multiple" count="*"/>
      <xsl:text>n</xsl:text>
      <xsl:number count="node()"/>
   </xsl:template>
   <xsl:template match="@*" mode="generate-id-2">
      <xsl:text>U.</xsl:text>
      <xsl:number level="multiple" count="*"/>
      <xsl:text>_</xsl:text>
      <xsl:value-of select="string-length(local-name(.))"/>
      <xsl:text>_</xsl:text>
      <xsl:value-of select="translate(name(),':','.')"/>
   </xsl:template>
   <!--Strip characters-->
   <xsl:template match="text()" priority="-1"/>
   <!--SCHEMA SETUP-->
   <xsl:template match="/">
      <svrl:schematron-output xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                              title="ISO Schematron rules"
                              schemaVersion="">
         <xsl:comment>
            <xsl:value-of select="$archiveDirParameter"/>   
		 <xsl:value-of select="$archiveNameParameter"/>  
		 <xsl:value-of select="$fileNameParameter"/>  
		 <xsl:value-of select="$fileDirParameter"/>
         </xsl:comment>
         <svrl:ns-prefix-in-attribute-values uri="http://www.tei-c.org/ns/1.0" prefix="tei"/>
         <svrl:ns-prefix-in-attribute-values uri="http://www.w3.org/2001/XMLSchema" prefix="xs"/>
         <svrl:ns-prefix-in-attribute-values uri="http://relaxng.org/ns/structure/1.0" prefix="rng"/>
         <svrl:ns-prefix-in-attribute-values uri="http://www.isocat.org/ns/dcr" prefix="dcr"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-att.datable.w3c-att-datable-w3c-when-1</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-att.datable.w3c-att-datable-w3c-when-1</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M5"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-att.datable.w3c-att-datable-w3c-from-2</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-att.datable.w3c-att-datable-w3c-from-2</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M6"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-att.datable.w3c-att-datable-w3c-to-3</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-att.datable.w3c-att-datable-w3c-to-3</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M7"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-att.datable-calendar-calendar-4</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-att.datable-calendar-calendar-4</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M8"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-att.measurement-att-measurement-unitRef-5</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-att.measurement-att-measurement-unitRef-5</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M9"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-att.typed-subtypeTyped-6</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-att.typed-subtypeTyped-6</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M10"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-att.pointing-targetLang-targetLang-7</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-att.pointing-targetLang-targetLang-7</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M11"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-att.spanning-spanTo-spanTo-2-8</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-att.spanning-spanTo-spanTo-2-8</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M12"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-att.styleDef-schemeVersion-schemeVersionRequiresScheme-9</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-att.styleDef-schemeVersion-schemeVersionRequiresScheme-9</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M13"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-p-p-10</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-p-p-10</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M14"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-p-abstractModel-structure-p-11</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-p-abstractModel-structure-p-11</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M15"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-p-abstractModel-structure-l-12</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-p-abstractModel-structure-l-12</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M16"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-desc-deprecationInfo-only-in-deprecated-13</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-desc-deprecationInfo-only-in-deprecated-13</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M17"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-choice-unclear-limit-14</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-choice-unclear-limit-14</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M18"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">isoschematron-constraint-dharma-gap-gap-15</xsl:attribute>
            <xsl:attribute name="name">isoschematron-constraint-dharma-gap-gap-15</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M19"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-rs-rs-rules-16</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-rs-rs-rules-16</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M20"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-num-valeur-or-interval-17</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-num-valeur-or-interval-17</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M21"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-date-attributes-18</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-date-attributes-18</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M22"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">isoschematron-constraint-dharma-expan-expan-19</xsl:attribute>
            <xsl:attribute name="name">isoschematron-constraint-dharma-expan-expan-19</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M23"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-ptr-ptrAtts-20</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-ptr-ptrAtts-20</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M24"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-ref-refAtts-21</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-ref-refAtts-21</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M25"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">isoschematron-constraint-dharma-list-lists-22</xsl:attribute>
            <xsl:attribute name="name">isoschematron-constraint-dharma-list-lists-22</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M26"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-list-gloss-list-must-have-labels-23</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-list-gloss-list-must-have-labels-23</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M27"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-head-head-childs-24</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-head-head-childs-24</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M28"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-note-note-25</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-note-note-25</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M29"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-milestone-att-unit-n-26</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-milestone-att-unit-n-26</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M30"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-citedRange-note-27</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-citedRange-note-27</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M31"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-bibl-siglum-28</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-bibl-siglum-28</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M32"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-l-mixed-verse-29</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-l-mixed-verse-29</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M33"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-l-abstractModel-structure-l-30</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-l-abstractModel-structure-l-30</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M34"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-lg-atleast1oflggapl-31</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-lg-atleast1oflggapl-31</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M35"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-lg-abstractModel-structure-l-32</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-lg-abstractModel-structure-l-32</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M36"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-quotation-quotationContents-33</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-quotation-quotationContents-33</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M37"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-change-responsability-34</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-change-responsability-34</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M38"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">isoschematron-constraint-dharma-div-div-37</xsl:attribute>
            <xsl:attribute name="name">isoschematron-constraint-dharma-div-div-37</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M39"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-div-abstractModel-structure-l-38</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-div-abstractModel-structure-l-38</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M40"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-div-abstractModel-structure-p-39</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-div-abstractModel-structure-p-39</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M41"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">isoschematron-constraint-dharma-ex-ex-40</xsl:attribute>
            <xsl:attribute name="name">isoschematron-constraint-dharma-ex-ex-40</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M42"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">isoschematron-constraint-dharma-am-ex-42</xsl:attribute>
            <xsl:attribute name="name">isoschematron-constraint-dharma-am-ex-42</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M44"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">isoschematron-constraint-dharma-space-space-43</xsl:attribute>
            <xsl:attribute name="name">isoschematron-constraint-dharma-space-space-43</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M45"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-subst-substContents1-44</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-subst-substContents1-44</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M46"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-certainty-usage-certainty-45</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-certainty-usage-certainty-45</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M47"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-ab-abstractModel-structure-ab-46</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-ab-abstractModel-structure-ab-46</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M48"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-ab-abstractModel-structure-l-47</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-ab-abstractModel-structure-l-47</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M49"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-seg-att-type-subtype-48</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-seg-att-type-subtype-48</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M50"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-dimensions-duplicateDim-49</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-dimensions-duplicateDim-49</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M51"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-origDate-origDate-50</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-origDate-origDate-50</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M52"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-signatures-signatures_in_msDesc-51</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-signatures-signatures_in_msDesc-51</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M53"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-msIdentifier-msId_minimal-52</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-msIdentifier-msId_minimal-52</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M54"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-persName-reference-53</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-persName-reference-53</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M55"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">isoschematron-constraint-dharma-placeName-div-54</xsl:attribute>
            <xsl:attribute name="name">isoschematron-constraint-dharma-placeName-div-54</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M56"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-objectIdentifier-objectIdentifier_minimal-55</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-objectIdentifier-objectIdentifier_minimal-55</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M57"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-app-one-lem-56</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-app-one-lem-56</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M58"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">isoschematron-constraint-dharma-listApp-div-57</xsl:attribute>
            <xsl:attribute name="name">isoschematron-constraint-dharma-listApp-div-57</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M59"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-lem-exclusion-inside-lem-58</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-lem-exclusion-inside-lem-58</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M60"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-rdg-exclusion-inside-lem-59</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-rdg-exclusion-inside-lem-59</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M61"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-rdgGrp-only1lem-60</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-rdgGrp-only1lem-60</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M62"/>
         <svrl:active-pattern>
            <xsl:attribute name="document">
               <xsl:value-of select="document-uri(/)"/>
            </xsl:attribute>
            <xsl:attribute name="id">schematron-constraint-dharma-variantEncoding-location-variantEncodingLocation-61</xsl:attribute>
            <xsl:attribute name="name">schematron-constraint-dharma-variantEncoding-location-variantEncodingLocation-61</xsl:attribute>
            <xsl:apply-templates/>
         </svrl:active-pattern>
         <xsl:apply-templates select="/" mode="M63"/>
      </svrl:schematron-output>
   </xsl:template>
   <!--SCHEMATRON PATTERNS-->
   <svrl:text xmlns:svrl="http://purl.oclc.org/dsdl/svrl">ISO Schematron rules</svrl:text>
   <!--PATTERN schematron-constraint-dharma-att.datable.w3c-att-datable-w3c-when-1-->

   <!--RULE -->
   <xsl:template match="tei:*[@when]" priority="1000" mode="M5">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:*[@when]"/>
      <!--REPORT nonfatal-->
      <xsl:if test="@notBefore|@notAfter|@from|@to">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                 test="@notBefore|@notAfter|@from|@to">
            <xsl:attribute name="role">nonfatal</xsl:attribute>
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>The @when attribute cannot be used with any other att.datable.w3c attributes.</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <xsl:apply-templates select="*" mode="M5"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M5"/>
   <xsl:template match="@*|node()" priority="-2" mode="M5">
      <xsl:apply-templates select="*" mode="M5"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-att.datable.w3c-att-datable-w3c-from-2-->

   <!--RULE -->
   <xsl:template match="tei:*[@from]" priority="1000" mode="M6">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:*[@from]"/>
      <!--REPORT nonfatal-->
      <xsl:if test="@notBefore">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl" test="@notBefore">
            <xsl:attribute name="role">nonfatal</xsl:attribute>
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>The @from and @notBefore attributes cannot be used together.</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <xsl:apply-templates select="*" mode="M6"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M6"/>
   <xsl:template match="@*|node()" priority="-2" mode="M6">
      <xsl:apply-templates select="*" mode="M6"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-att.datable.w3c-att-datable-w3c-to-3-->

   <!--RULE -->
   <xsl:template match="tei:*[@to]" priority="1000" mode="M7">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:*[@to]"/>
      <!--REPORT nonfatal-->
      <xsl:if test="@notAfter">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl" test="@notAfter">
            <xsl:attribute name="role">nonfatal</xsl:attribute>
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>The @to and @notAfter attributes cannot be used together.</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <xsl:apply-templates select="*" mode="M7"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M7"/>
   <xsl:template match="@*|node()" priority="-2" mode="M7">
      <xsl:apply-templates select="*" mode="M7"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-att.datable-calendar-calendar-4-->

   <!--RULE -->
   <xsl:template match="tei:*[@calendar]" priority="1000" mode="M8">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:*[@calendar]"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="string-length(.) gt 0"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl" test="string-length(.) gt 0">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text> @calendar indicates the system or calendar to
              which the date represented by the content of this element belongs, but this
              <xsl:text/>
                  <xsl:value-of select="name(.)"/>
                  <xsl:text/> element has no textual content.</svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M8"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M8"/>
   <xsl:template match="@*|node()" priority="-2" mode="M8">
      <xsl:apply-templates select="*" mode="M8"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-att.measurement-att-measurement-unitRef-5-->

   <!--RULE -->
   <xsl:template match="tei:*[@unitRef]" priority="1000" mode="M9">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:*[@unitRef]"/>
      <!--REPORT info-->
      <xsl:if test="@unit">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl" test="@unit">
            <xsl:attribute name="role">info</xsl:attribute>
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>The @unit attribute may be unnecessary when @unitRef is present.</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <xsl:apply-templates select="*" mode="M9"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M9"/>
   <xsl:template match="@*|node()" priority="-2" mode="M9">
      <xsl:apply-templates select="*" mode="M9"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-att.typed-subtypeTyped-6-->

   <!--RULE -->
   <xsl:template match="tei:*[@subtype]" priority="1000" mode="M10">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:*[@subtype]"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="@type"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl" test="@type">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>The <xsl:text/>
                  <xsl:value-of select="name(.)"/>
                  <xsl:text/> element should not be categorized in detail with @subtype unless also categorized in general with @type</svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M10"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M10"/>
   <xsl:template match="@*|node()" priority="-2" mode="M10">
      <xsl:apply-templates select="*" mode="M10"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-att.pointing-targetLang-targetLang-7-->

   <!--RULE -->
   <xsl:template match="tei:*[not(self::tei:schemaSpec)][@targetLang]"
                 priority="1000"
                 mode="M11">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                       context="tei:*[not(self::tei:schemaSpec)][@targetLang]"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="@target"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl" test="@target">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>@targetLang should only be used on <xsl:text/>
                  <xsl:value-of select="name(.)"/>
                  <xsl:text/> if @target is specified.</svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M11"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M11"/>
   <xsl:template match="@*|node()" priority="-2" mode="M11">
      <xsl:apply-templates select="*" mode="M11"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-att.spanning-spanTo-spanTo-2-8-->

   <!--RULE -->
   <xsl:template match="tei:*[@spanTo]" priority="1000" mode="M12">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:*[@spanTo]"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="id(substring(@spanTo,2)) and following::*[@xml:id=substring(current()/@spanTo,2)]"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                test="id(substring(@spanTo,2)) and following::*[@xml:id=substring(current()/@spanTo,2)]">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>
The element indicated by @spanTo (<xsl:text/>
                  <xsl:value-of select="@spanTo"/>
                  <xsl:text/>) must follow the current element <xsl:text/>
                  <xsl:value-of select="name(.)"/>
                  <xsl:text/>
               </svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M12"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M12"/>
   <xsl:template match="@*|node()" priority="-2" mode="M12">
      <xsl:apply-templates select="*" mode="M12"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-att.styleDef-schemeVersion-schemeVersionRequiresScheme-9-->

   <!--RULE -->
   <xsl:template match="tei:*[@schemeVersion]" priority="1000" mode="M13">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:*[@schemeVersion]"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="@scheme and not(@scheme = 'free')"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                test="@scheme and not(@scheme = 'free')">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>
              @schemeVersion can only be used if @scheme is specified.
            </svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M13"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M13"/>
   <xsl:template match="@*|node()" priority="-2" mode="M13">
      <xsl:apply-templates select="*" mode="M13"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-p-p-10-->

   <!--RULE -->
   <xsl:template match="tei:p" priority="1000" mode="M14">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:p"/>
      <!--REPORT -->
      <xsl:if test="@rend='stanza' and not(ancestor::tei:div[@type='translation'])">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                 test="@rend='stanza' and not(ancestor::tei:div[@type='translation'])">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>@rend='stanza' can only be used in div[@type='translation']</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <xsl:apply-templates select="*" mode="M14"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M14"/>
   <xsl:template match="@*|node()" priority="-2" mode="M14">
      <xsl:apply-templates select="*" mode="M14"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-p-abstractModel-structure-p-11-->

   <!--RULE -->
   <xsl:template match="tei:p" priority="1000" mode="M15">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:p"/>
      <!--REPORT -->
      <xsl:if test="not(ancestor::tei:floatingText) and (ancestor::tei:p or ancestor::tei:ab)          and not(parent::tei:exemplum                |parent::tei:item                |parent::tei:note                |parent::tei:q                |parent::tei:quote                |parent::tei:remarks                |parent::tei:said                |parent::tei:sp                |parent::tei:stage                |parent::tei:cell                |parent::tei:figure                )">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                 test="not(ancestor::tei:floatingText) and (ancestor::tei:p or ancestor::tei:ab) and not(parent::tei:exemplum |parent::tei:item |parent::tei:note |parent::tei:q |parent::tei:quote |parent::tei:remarks |parent::tei:said |parent::tei:sp |parent::tei:stage |parent::tei:cell |parent::tei:figure )">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>
        Abstract model violation: Paragraphs may not occur inside other paragraphs or ab elements.
      </svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <xsl:apply-templates select="*" mode="M15"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M15"/>
   <xsl:template match="@*|node()" priority="-2" mode="M15">
      <xsl:apply-templates select="*" mode="M15"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-p-abstractModel-structure-l-12-->

   <!--RULE -->
   <xsl:template match="tei:p" priority="1000" mode="M16">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:p"/>
      <!--REPORT -->
      <xsl:if test="ancestor::tei:l[not(.//tei:note//tei:p[. = current()])]">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                 test="ancestor::tei:l[not(.//tei:note//tei:p[. = current()])]">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>
        Abstract model violation: Lines may not contain higher-level structural elements such as div, p, or ab.
      </svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <xsl:apply-templates select="*" mode="M16"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M16"/>
   <xsl:template match="@*|node()" priority="-2" mode="M16">
      <xsl:apply-templates select="*" mode="M16"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-desc-deprecationInfo-only-in-deprecated-13-->

   <!--RULE -->
   <xsl:template match="tei:desc[ @type eq 'deprecationInfo']"
                 priority="1000"
                 mode="M17">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                       context="tei:desc[ @type eq 'deprecationInfo']"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="../@validUntil"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl" test="../@validUntil">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>Information about a
	deprecation should only be present in a specification element
	that is being deprecated: that is, only an element that has a
	@validUntil attribute should have a child &lt;desc
	type="deprecationInfo"&gt;.</svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M17"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M17"/>
   <xsl:template match="@*|node()" priority="-2" mode="M17">
      <xsl:apply-templates select="*" mode="M17"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-choice-unclear-limit-14-->

   <!--RULE -->
   <xsl:template match="tei:choice" priority="1000" mode="M18">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:choice"/>
      <!--REPORT -->
      <xsl:if test="child::tei:unclear and count(child::tei:unclear) &gt; 3">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                 test="child::tei:unclear and count(child::tei:unclear) &gt; 3">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>Choice
                            can contained only maximum 3 unclear
                            elements</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <xsl:apply-templates select="*" mode="M18"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M18"/>
   <xsl:template match="@*|node()" priority="-2" mode="M18">
      <xsl:apply-templates select="*" mode="M18"/>
   </xsl:template>
   <!--PATTERN isoschematron-constraint-dharma-gap-gap-15-->

   <!--RULE -->
   <xsl:template match="tei:gap" priority="1003" mode="M19">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:gap"/>
      <!--REPORT -->
      <xsl:if test="@quantity and @extent">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl" test="@quantity and @extent">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>gap may have @quantity (a figure) or
                            @extent (a descriptive text value) but not both</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <!--REPORT -->
      <xsl:if test="@quantity and not(@unit)">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl" test="@quantity and not(@unit)">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>If gap has @quantity then @unit is
                            required</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <!--REPORT -->
      <xsl:if test="not(@reason='ellipsis') and ancestor::tei:supplied[not(@reason='undefined')]">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                 test="not(@reason='ellipsis') and ancestor::tei:supplied[not(@reason='undefined')]">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>gap may not appear within supplied text</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <!--REPORT -->
      <xsl:if test="@precision and not(@quantity)">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                 test="@precision and not(@quantity)">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>@precision can be use only with
                            @quantity</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <!--REPORT -->
      <xsl:if test="ancestor::tei:div[@type='aparatus'] and not(@reason)">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                 test="ancestor::tei:div[@type='aparatus'] and not(@reason)">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>Only @reason
                            is mandatory in
                            div[@type='translation']</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <xsl:apply-templates select="*" mode="M19"/>
   </xsl:template>
   <!--RULE -->
   <xsl:template match="tei:gap[@reason='ellipsis']" priority="1002" mode="M19">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                       context="tei:gap[@reason='ellipsis']"/>
      <!--REPORT -->
      <xsl:if test="not(ancestor::tei:div[@type='apparatus'] or ancestor::tei:div[@type='translation'])">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                 test="not(ancestor::tei:div[@type='apparatus'] or ancestor::tei:div[@type='translation'])">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text> The element gap with @reason='ellipsis' can only be used inside the
                            apparatus or in translation.</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <xsl:apply-templates select="*" mode="M19"/>
   </xsl:template>
   <!--RULE -->
   <xsl:template match="tei:gap[@unit='component']" priority="1001" mode="M19">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                       context="tei:gap[@unit='component']"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="parent::tei:seg[@type='component']"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                test="parent::tei:seg[@type='component']">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>Gap with the attribute
                            @unit="component" can only be used inside seg with the
                            @type="component". </svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M19"/>
   </xsl:template>
   <!--RULE -->
   <xsl:template match="tei:gap[@unit='line' and @quantity] "
                 priority="1000"
                 mode="M19">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                       context="tei:gap[@unit='line' and @quantity] "/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="@precision='low' or child::tei:certainty"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                test="@precision='low' or child::tei:certainty">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>The element gap with
                            @quantity and @unit="line" expect either the use of @precision="low" or
                            the element certainty.</svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M19"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M19"/>
   <xsl:template match="@*|node()" priority="-2" mode="M19">
      <xsl:apply-templates select="*" mode="M19"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-rs-rs-rules-16-->

   <!--RULE -->
   <xsl:template match="tei:rs[@type='month']" priority="1012" mode="M20">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:rs[@type='month']"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="@key='caitra' or @key='vaisakha' or @key='jyaistha' or @key='asadha' or @key='sravana' or @key='bhadrapada' or @key='asvina' or @key='karttika' or @key='margasira' or @key='pausa' or @key='magha' or @key='phalguna'"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                test="@key='caitra' or @key='vaisakha' or @key='jyaistha' or @key='asadha' or @key='sravana' or @key='bhadrapada' or @key='asvina' or @key='karttika' or @key='margasira' or @key='pausa' or @key='magha' or @key='phalguna'">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>
                                with the @type="month", you should used one of the following values: caitra, vaisakha, jyaistha, asadha, sravana, bhadrapada, asvina, karttika, margasira, pausa, magha, phalguna.
                            </svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M20"/>
   </xsl:template>
   <!--RULE -->
   <xsl:template match="tei:rs[@type='fortnight']" priority="1011" mode="M20">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                       context="tei:rs[@type='fortnight']"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="@subtype='dark' or @subtype='bright'"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                test="@subtype='dark' or @subtype='bright'">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>
                                    with the @type="fortnight", you should used either @subtype="dark" or @subtype="bright".
                                </svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M20"/>
   </xsl:template>
   <!--RULE -->
   <xsl:template match="tei:rs[@type='tithi']" priority="1010" mode="M20">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:rs[@type='tithi']"/>
      <!--REPORT -->
      <xsl:if test="@key">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl" test="@key">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>@key shouldn't be used with tei:rs[@type='tithi'], favor @n.
                                </svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <xsl:apply-templates select="*" mode="M20"/>
   </xsl:template>
   <!--RULE -->
   <xsl:template match="tei:rs[@type='naksatra']" priority="1009" mode="M20">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                       context="tei:rs[@type='naksatra']"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="@key='krttika'or @key='rohini'or @key='mrgasirsa'or @key='ardra'or @key='punarvasu'or @key='pusya'or @key='aslesa'or @key='magha'or @key='purva-phalguni'or @key='uttara-phalguni'or @key='hasta'or @key='citra'or @key='svati'or @key='visakha'or @key='anuradha'or @key='jyestha'or @key='mula'or @key='purva-asadha'or @key='uttara-asadha'or @key='sravana'or @key='dhanistha'or @key='satabhisaj'or @key='purva-bhadrapada'or @key='uttara-bhadrapada'or @key='revati'or @key='asvini'or @key='bharani'"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                test="@key='krttika'or @key='rohini'or @key='mrgasirsa'or @key='ardra'or @key='punarvasu'or @key='pusya'or @key='aslesa'or @key='magha'or @key='purva-phalguni'or @key='uttara-phalguni'or @key='hasta'or @key='citra'or @key='svati'or @key='visakha'or @key='anuradha'or @key='jyestha'or @key='mula'or @key='purva-asadha'or @key='uttara-asadha'or @key='sravana'or @key='dhanistha'or @key='satabhisaj'or @key='purva-bhadrapada'or @key='uttara-bhadrapada'or @key='revati'or @key='asvini'or @key='bharani'">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>with the @type="naksatra", you can only used one of the following values for @key: krttika, rohini, mrgasirsa, ardra, punarvasu, pusya, aslesa, magha, purva-phalguni, uttara-phalguni, hasta, citra, svati, visakha, anuradha, jyestha, mula, purva-asadha, uttara-asadha, sravana, dhanistha, satabhisaj, purva-bhadrapada, uttara-bhadrapada, revati, asvini, bharani</svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M20"/>
   </xsl:template>
   <!--RULE -->
   <xsl:template match="tei:rs[@type='sadvara']" priority="1008" mode="M20">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                       context="tei:rs[@type='sadvara']"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="@key='tunglai' or @key='hariyang' or @key='wurukung' or @key='paniruan' or @key='was' or @key='mawulu'"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                test="@key='tunglai' or @key='hariyang' or @key='wurukung' or @key='paniruan' or @key='was' or @key='mawulu'">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>With the @type='sadvara', you can only use one of the following values: tunglai, hariyang, wurukung, paniruan, was, mawulu.
                            </svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M20"/>
   </xsl:template>
   <!--RULE -->
   <xsl:template match="tei:rs[@type='pancavara']" priority="1007" mode="M20">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                       context="tei:rs[@type='pancavara']"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="@key='pahing' or @key='pon' or @key='wagai' or @key='kaliwuan' or @key='umanis'"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                test="@key='pahing' or @key='pon' or @key='wagai' or @key='kaliwuan' or @key='umanis'">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>With the @type='pancavara', you can only use one of the following values: pahing, pon, wagai, kaliwuan, umanis.
                                </svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M20"/>
   </xsl:template>
   <!--RULE -->
   <xsl:template match="tei:rs[@type='season']" priority="1006" mode="M20">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                       context="tei:rs[@type='season']"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="@key='hemanta' or @key='grisma' or @key='varsa'"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                test="@key='hemanta' or @key='grisma' or @key='varsa'">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>With the @type='season', you can only use one of the following values: hemanta, grisma, varsa.
                                </svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M20"/>
   </xsl:template>
   <!--RULE -->
   <xsl:template match="tei:rs[@type='wuku']" priority="1005" mode="M20">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:rs[@type='wuku']"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="@key='sinta' or @key='landep' or @key='wukir' or @key='kurantil' or @key='tolu' or @key='gumbreg' or @key='warigalit' or @key='warigagung' or @key='julung' or @key='sungsang' or @key='galungan' or @key='dungulan' or @key='kuningan' or @key='langki' or @key='madasiha' or @key='pujut' or @key='pahang' or @key='kuruwlut' or @key='marakih' or @key='tambir' or @key='madangkungan' or @key='mahatal' or @key='wuyai' or @key='manahil' or @key='prangbakat' or @key='balamuki' or @key='wugu' or @key='wayang' or @key='kulawu' or @key='dukut' or @key='watugunung'"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                test="@key='sinta' or @key='landep' or @key='wukir' or @key='kurantil' or @key='tolu' or @key='gumbreg' or @key='warigalit' or @key='warigagung' or @key='julung' or @key='sungsang' or @key='galungan' or @key='dungulan' or @key='kuningan' or @key='langki' or @key='madasiha' or @key='pujut' or @key='pahang' or @key='kuruwlut' or @key='marakih' or @key='tambir' or @key='madangkungan' or @key='mahatal' or @key='wuyai' or @key='manahil' or @key='prangbakat' or @key='balamuki' or @key='wugu' or @key='wayang' or @key='kulawu' or @key='dukut' or @key='watugunung'">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>With the @type='wuku' or you can only use one of the following values: sinta or landep or wukir or kurantil or tolu or gumbreg or warigalit or warigagung or julung or sungsang or galungan or dungulan or kuningan or langki or madasiha or pujut or pahang or kuruwlut or marakih or tambir or madangkungan or mahatal or wuyai or manahil or prangbakat or balamuki or wugu or wayang or kulawu or dukut or watugunung.
                                </svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M20"/>
   </xsl:template>
   <!--RULE -->
   <xsl:template match="tei:rs[@type='chinese']" priority="1004" mode="M20">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                       context="tei:rs[@type='chinese']"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="@key='rat' or @key='buffalo-ox' or @key='tiger' or @key='hare-cat' or @key='dragon' or @key='snake' or @key='horse' or @key='goat' or @key='monkey' or @key='cock' or @key='dog' or @key='pig'"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                test="@key='rat' or @key='buffalo-ox' or @key='tiger' or @key='hare-cat' or @key='dragon' or @key='snake' or @key='horse' or @key='goat' or @key='monkey' or @key='cock' or @key='dog' or @key='pig'">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>With the @type='chinese', you can only use one of the following values: rat, buffalo-ox, tiger, hare-cat, dragon, snake, horse, goat, monkey, cock, dog, pig.
                                </svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M20"/>
   </xsl:template>
   <!--RULE -->
   <xsl:template match="tei:rs[@type='solstice']" priority="1003" mode="M20">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                       context="tei:rs[@type='solstice']"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="@key='winter' or @key='summer'"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                test="@key='winter' or @key='summer'">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>With the @type='solstice', you can only use one of the following values: winter or summer.
                                </svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M20"/>
   </xsl:template>
   <!--RULE -->
   <xsl:template match="tei:rs[@type='equinox']" priority="1002" mode="M20">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                       context="tei:rs[@type='equinox']"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="@key='autumn' or @key='spring'"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                test="@key='autumn' or @key='spring'">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>With the @type='equinox', you can only use one of the following values: autumn or spring.
                                </svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M20"/>
   </xsl:template>
   <!--RULE -->
   <xsl:template match="tei:rs[@type='eclipse']" priority="1001" mode="M20">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                       context="tei:rs[@type='eclipse']"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="@key='lunar' or @key='solar'"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                test="@key='lunar' or @key='solar'">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>With the @type='eclipse', you can only use one of the following values: lunar or solar.
                                </svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M20"/>
   </xsl:template>
   <!--RULE -->
   <xsl:template match="tei:rs[@type='individual-masc' or @type='individual-fem' or @type='individual-other']"
                 priority="1000"
                 mode="M20">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                       context="tei:rs[@type='individual-masc' or @type='individual-fem' or @type='individual-other']"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="@subtype='deity' or @subtype='godLegalEntity' or @subtype='god_child' or @subtype='ruler' or @subtype='ruler_spouse' or @subtype='ruler_child' or @subtype='subordinateRuler' or @subtype='royalPreceptor' or @subtype='noble' or @subtype='landlord' or @subtype='chief' or @subtype='priest' or @subtype='brahmin' or @subtype='monk' or @subtype='cleric' or @subtype='officiant' or @subtype='officer' or @subtype='ascetic' or @subtype='hermit' or @subtype='merchant' or @subtype='artisan' or @subtype='brahminDelegate' or @subtype='regionalDelegate' or @subtype='dancer' or @subtype='singer' or @subtype='peasant' or @subtype='shepherd' or @subtype='slave' or @subtype='fieldWork' or @subtype='unknown'"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                test="@subtype='deity' or @subtype='godLegalEntity' or @subtype='god_child' or @subtype='ruler' or @subtype='ruler_spouse' or @subtype='ruler_child' or @subtype='subordinateRuler' or @subtype='royalPreceptor' or @subtype='noble' or @subtype='landlord' or @subtype='chief' or @subtype='priest' or @subtype='brahmin' or @subtype='monk' or @subtype='cleric' or @subtype='officiant' or @subtype='officer' or @subtype='ascetic' or @subtype='hermit' or @subtype='merchant' or @subtype='artisan' or @subtype='brahminDelegate' or @subtype='regionalDelegate' or @subtype='dancer' or @subtype='singer' or @subtype='peasant' or @subtype='shepherd' or @subtype='slave' or @subtype='fieldWork' or @subtype='unknown'">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>one of the following @subtype value can only work with @type='individual'.</svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M20"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M20"/>
   <xsl:template match="@*|node()" priority="-2" mode="M20">
      <xsl:apply-templates select="*" mode="M20"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-num-valeur-or-interval-17-->

   <!--RULE -->
   <xsl:template match="tei:num" priority="1000" mode="M21">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:num"/>
      <!--REPORT -->
      <xsl:if test="@value and (@atMost or @atLeast)">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                 test="@value and (@atMost or @atLeast)">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>@value can not be used with the
                            attributes of date range</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <!--REPORT -->
      <xsl:if test="@atMost and not(@atLeast)">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                 test="@atMost and not(@atLeast)">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>@atLeast is expected with
                            @atMost</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <!--REPORT -->
      <xsl:if test="@atLeast and not(@atMost)">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                 test="@atLeast and not(@atMost)">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>@atMost
                            is expected with @atLeast</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <xsl:apply-templates select="*" mode="M21"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M21"/>
   <xsl:template match="@*|node()" priority="-2" mode="M21">
      <xsl:apply-templates select="*" mode="M21"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-date-attributes-18-->

   <!--RULE -->
   <xsl:template match="tei:date[not(parent::tei:bibl)][@notBefore-custom or @notAfter-custom]"
                 priority="1004"
                 mode="M22">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                       context="tei:date[not(parent::tei:bibl)][@notBefore-custom or @notAfter-custom]"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="@notBefore-custom and @notAfter-custom"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                test="@notBefore-custom and @notAfter-custom">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>@notBefore-custom and @notAfter-custom must be used together</svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M22"/>
   </xsl:template>
   <!--RULE -->
   <xsl:template match="tei:date[not(parent::tei:bibl)][@notBefore or @notAfter]"
                 priority="1003"
                 mode="M22">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                       context="tei:date[not(parent::tei:bibl)][@notBefore or @notAfter]"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="@notBefore and @notAfter"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl" test="@notBefore and @notAfter">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>@notBefore and @notAfter must be used together</svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M22"/>
   </xsl:template>
   <!--RULE -->
   <xsl:template match="tei:date[not(parent::tei:bibl)][@from-custom or @to-custom]"
                 priority="1002"
                 mode="M22">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                       context="tei:date[not(parent::tei:bibl)][@from-custom or @to-custom]"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="@from-custom and @to-custom"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                test="@from-custom and @to-custom">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>The attributes @from-custom and @to-custom must be used together</svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M22"/>
   </xsl:template>
   <!--RULE -->
   <xsl:template match="tei:date[not(parent::tei:bibl)][@when-custom or @notAfter-custom or @notBefore-custom or @from-custom or @to-custom]"
                 priority="1001"
                 mode="M22">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                       context="tei:date[not(parent::tei:bibl)][@when-custom or @notAfter-custom or @notBefore-custom or @from-custom or @to-custom]"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="@datingMethod"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl" test="@datingMethod">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>When using a custom attribute such as @when-custom or @notAfter-custom or @notBefore-custom, the attribute @datingMethod is mandatory and should declare the calendar used to convert the dates expressed in those previous attributes.</svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M22"/>
   </xsl:template>
   <!--RULE -->
   <xsl:template match="tei:date[not(parent::tei:bibl)][@when-custom or @notAfter-custom or @notBefore-custom or @from-custom or @to-custom]"
                 priority="1000"
                 mode="M22">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                       context="tei:date[not(parent::tei:bibl)][@when-custom or @notAfter-custom or @notBefore-custom or @from-custom or @to-custom]"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="matches(., '\d\d\d\d')"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl" test="matches(., '\d\d\d\d')">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>Only the year in a 4 digits format can be given for the vernacular calendar.</svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M22"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M22"/>
   <xsl:template match="@*|node()" priority="-2" mode="M22">
      <xsl:apply-templates select="*" mode="M22"/>
   </xsl:template>
   <!--PATTERN isoschematron-constraint-dharma-expan-expan-19-->

   <!--RULE -->
   <xsl:template match="tei:expan" priority="1000" mode="M23">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:expan"/>
      <!--REPORT -->
      <xsl:if test="not(descendant::tei:ex or descendant::tei:abbr)">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                 test="not(descendant::tei:ex or descendant::tei:abbr)">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>expan should contain ex or abbr</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <xsl:apply-templates select="*" mode="M23"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M23"/>
   <xsl:template match="@*|node()" priority="-2" mode="M23">
      <xsl:apply-templates select="*" mode="M23"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-ptr-ptrAtts-20-->

   <!--RULE -->
   <xsl:template match="tei:ptr" priority="1000" mode="M24">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:ptr"/>
      <!--REPORT -->
      <xsl:if test="@target and @cRef">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl" test="@target and @cRef">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>Only one of the
attributes @target and @cRef may be supplied on <xsl:text/>
               <xsl:value-of select="name(.)"/>
               <xsl:text/>.</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <xsl:apply-templates select="*" mode="M24"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M24"/>
   <xsl:template match="@*|node()" priority="-2" mode="M24">
      <xsl:apply-templates select="*" mode="M24"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-ref-refAtts-21-->

   <!--RULE -->
   <xsl:template match="tei:ref" priority="1000" mode="M25">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:ref"/>
      <!--REPORT -->
      <xsl:if test="@target and @cRef">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl" test="@target and @cRef">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>Only one of the
	attributes @target' and @cRef' may be supplied on <xsl:text/>
               <xsl:value-of select="name(.)"/>
               <xsl:text/>
            </svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <xsl:apply-templates select="*" mode="M25"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M25"/>
   <xsl:template match="@*|node()" priority="-2" mode="M25">
      <xsl:apply-templates select="*" mode="M25"/>
   </xsl:template>
   <!--PATTERN isoschematron-constraint-dharma-list-lists-22-->

   <!--RULE -->
   <xsl:template match="tei:list" priority="1000" mode="M26">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:list"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="parent::tei:p"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl" test="parent::tei:p">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>List can only be used inside a paragraph element.</svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M26"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M26"/>
   <xsl:template match="@*|node()" priority="-2" mode="M26">
      <xsl:apply-templates select="*" mode="M26"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-list-gloss-list-must-have-labels-23-->

   <!--RULE -->
   <xsl:template match="tei:list[@type='gloss']" priority="1000" mode="M27">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                       context="tei:list[@type='gloss']"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="tei:label"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl" test="tei:label">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>The content of a "gloss" list should include a sequence of one or more pairs of a label element followed by an item element</svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M27"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M27"/>
   <xsl:template match="@*|node()" priority="-2" mode="M27">
      <xsl:apply-templates select="*" mode="M27"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-head-head-childs-24-->

   <!--RULE -->
   <xsl:template match="tei:head/child::tei:*" priority="1000" mode="M28">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:head/child::tei:*"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="local-name()= ('foreign')"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                test="local-name()= ('foreign')">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>Foreign is the only element allowed as
                            child of the element head</svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M28"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M28"/>
   <xsl:template match="@*|node()" priority="-2" mode="M28">
      <xsl:apply-templates select="*" mode="M28"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-note-note-25-->

   <!--RULE -->
   <xsl:template match="tei:note" priority="1002" mode="M29">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:note"/>
      <!--REPORT -->
      <xsl:if test="parent::tei:bibl and ancestor::tei:listBibl and following-sibling::tei:*">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                 test="parent::tei:bibl and ancestor::tei:listBibl and following-sibling::tei:*">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>Note should the last element of the
                            biliography</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <xsl:apply-templates select="*" mode="M29"/>
   </xsl:template>
   <!--RULE -->
   <xsl:template match="tei:note[parent::tei:app]" priority="1001" mode="M29">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                       context="tei:note[parent::tei:app]"/>
      <!--REPORT -->
      <xsl:if test="following-sibling::tei:*[not(local-name () = 'note')]">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                 test="following-sibling::tei:*[not(local-name () = 'note')]">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>Note(s) be should the last element
                            of the apparatus entry</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <xsl:apply-templates select="*" mode="M29"/>
   </xsl:template>
   <!--RULE -->
   <xsl:template match="tei:note" priority="1000" mode="M29">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:note"/>
      <!--REPORT -->
      <xsl:if test="child::tei:note">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl" test="child::tei:note">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>Note(s) may not
                            contain further notes (this is not a technical requirement but a
                            convention we shall observe to reduce
                            complication)</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <xsl:apply-templates select="*" mode="M29"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M29"/>
   <xsl:template match="@*|node()" priority="-2" mode="M29">
      <xsl:apply-templates select="*" mode="M29"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-milestone-att-unit-n-26-->

   <!--RULE -->
   <xsl:template match="tei:milestone" priority="1004" mode="M30">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:milestone"/>
      <!--REPORT -->
      <xsl:if test="not(@unit and @n)">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl" test="not(@unit and @n)">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text> for milestone using the attribut @unit, the
                            attribute @n is mandatory</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <xsl:apply-templates select="*" mode="M30"/>
   </xsl:template>
   <!--RULE -->
   <xsl:template match="tei:milestone[@type='yati']" priority="1003" mode="M30">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                       context="tei:milestone[@type='yati']"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="@type='yati' and @break='no'"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                test="@type='yati' and @break='no'">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>Caesuras work with both @type='yati'
                            and @break='no'.</svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M30"/>
   </xsl:template>
   <!--RULE -->
   <xsl:template match="tei:milestone[@type='ref']" priority="1002" mode="M30">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                       context="tei:milestone[@type='ref']"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="ancestor::tei:div[@type='translation']"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                test="ancestor::tei:div[@type='translation']">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>@type='ref' can only be
                            used inside the translation part of the
                            edition</svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M30"/>
   </xsl:template>
   <!--RULE -->
   <xsl:template match="tei:milestone[@type='ref']" priority="1001" mode="M30">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                       context="tei:milestone[@type='ref']"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="@unit='stanza' or @unit='line'"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                test="@unit='stanza' or @unit='line'">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>@type='ref' requires the use of
                            @unit="stanza" or @unit="line'</svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M30"/>
   </xsl:template>
   <!--RULE -->
   <xsl:template match="tei:milestone[@type='ref']" priority="1000" mode="M30">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                       context="tei:milestone[@type='ref']"/>
      <!--REPORT -->
      <xsl:if test="not(@n)">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl" test="not(@n)">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>@n is
                            mandatory with
                            milestone/@type="ref"</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <xsl:apply-templates select="*" mode="M30"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M30"/>
   <xsl:template match="@*|node()" priority="-2" mode="M30">
      <xsl:apply-templates select="*" mode="M30"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-citedRange-note-27-->

   <!--RULE -->
   <xsl:template match="tei:citedRange" priority="1000" mode="M31">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:citedRange"/>
      <!--REPORT -->
      <xsl:if test="child::tei:note and ancestor::tei:listBibl">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                 test="child::tei:note and ancestor::tei:listBibl">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>Note can not be used
                            as a child of the element citedRange, only as a sibling of this
                            element</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <xsl:apply-templates select="*" mode="M31"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M31"/>
   <xsl:template match="@*|node()" priority="-2" mode="M31">
      <xsl:apply-templates select="*" mode="M31"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-bibl-siglum-28-->

   <!--RULE -->
   <xsl:template match="tei:bibl[ancestor::tei:listBibl]" priority="1001" mode="M32">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                       context="tei:bibl[ancestor::tei:listBibl]"/>
      <!--REPORT -->
      <xsl:if test="child::tei:note[following-sibling::tei:*]">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                 test="child::tei:note[following-sibling::tei:*]">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>Note should be the last
                            element of the bibl</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <xsl:apply-templates select="*" mode="M32"/>
   </xsl:template>
   <!--RULE -->
   <xsl:template match="tei:bibl[child::tei:note]" priority="1000" mode="M32">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                       context="tei:bibl[child::tei:note]"/>
      <!--REPORT -->
      <xsl:if test="ancestor::tei:div[@type='commentary'] or ancestor::tei:div[@type='apparatus'] or ancestor::tei:p[parent::tei:div[@type='bibliography']]">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                 test="ancestor::tei:div[@type='commentary'] or ancestor::tei:div[@type='apparatus'] or ancestor::tei:p[parent::tei:div[@type='bibliography']]">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>In the commentary, apparatus and the epigraphic lemma, note inside bibl
                            is prohibited. Add the note element right after the bibl
                            element.</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <xsl:apply-templates select="*" mode="M32"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M32"/>
   <xsl:template match="@*|node()" priority="-2" mode="M32">
      <xsl:apply-templates select="*" mode="M32"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-l-mixed-verse-29-->

   <!--RULE -->
   <xsl:template match="tei:l[parent::tei:lg[@met='mixed']]"
                 priority="1000"
                 mode="M33">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                       context="tei:l[parent::tei:lg[@met='mixed']]"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="self::tei:l[@real or @met]"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                test="self::tei:l[@real or @met]">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>In a stanza identify as "mixed", the children verse lines must have at least an attribute @met or @real.</svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M33"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M33"/>
   <xsl:template match="@*|node()" priority="-2" mode="M33">
      <xsl:apply-templates select="*" mode="M33"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-l-abstractModel-structure-l-30-->

   <!--RULE -->
   <xsl:template match="tei:l" priority="1000" mode="M34">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:l"/>
      <!--REPORT -->
      <xsl:if test="ancestor::tei:l[not(.//tei:note//tei:l[. = current()])]">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                 test="ancestor::tei:l[not(.//tei:note//tei:l[. = current()])]">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>
        Abstract model violation: Lines may not contain lines or lg elements.
      </svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <xsl:apply-templates select="*" mode="M34"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M34"/>
   <xsl:template match="@*|node()" priority="-2" mode="M34">
      <xsl:apply-templates select="*" mode="M34"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-lg-atleast1oflggapl-31-->

   <!--RULE -->
   <xsl:template match="tei:lg" priority="1000" mode="M35">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:lg"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="count(descendant::tei:lg|descendant::tei:l|descendant::tei:gap) &gt; 0"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                test="count(descendant::tei:lg|descendant::tei:l|descendant::tei:gap) &gt; 0">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>An lg element
        must contain at least one child l, lg, or gap element.</svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M35"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M35"/>
   <xsl:template match="@*|node()" priority="-2" mode="M35">
      <xsl:apply-templates select="*" mode="M35"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-lg-abstractModel-structure-l-32-->

   <!--RULE -->
   <xsl:template match="tei:lg" priority="1000" mode="M36">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:lg"/>
      <!--REPORT -->
      <xsl:if test="ancestor::tei:l[not(.//tei:note//tei:lg[. = current()])]">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                 test="ancestor::tei:l[not(.//tei:note//tei:lg[. = current()])]">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>
        Abstract model violation: Lines may not contain line groups.
      </svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <xsl:apply-templates select="*" mode="M36"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M36"/>
   <xsl:template match="@*|node()" priority="-2" mode="M36">
      <xsl:apply-templates select="*" mode="M36"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-quotation-quotationContents-33-->

   <!--RULE -->
   <xsl:template match="tei:quotation" priority="1000" mode="M37">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:quotation"/>
      <!--REPORT -->
      <xsl:if test="not(@marks) and not (tei:p)">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                 test="not(@marks) and not (tei:p)">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>
On <xsl:text/>
               <xsl:value-of select="name(.)"/>
               <xsl:text/>, either the @marks attribute should be used, or a paragraph of description provided</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <xsl:apply-templates select="*" mode="M37"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M37"/>
   <xsl:template match="@*|node()" priority="-2" mode="M37">
      <xsl:apply-templates select="*" mode="M37"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-change-responsability-34-->

   <!--RULE -->
   <xsl:template match="@who" priority="1000" mode="M38">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="@who"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="starts-with(.,'part:')"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl" test="starts-with(.,'part:')">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>Project members prefix is
                            part:</svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M38"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M38"/>
   <xsl:template match="@*|node()" priority="-2" mode="M38">
      <xsl:apply-templates select="*" mode="M38"/>
   </xsl:template>
   <!--PATTERN isoschematron-constraint-dharma-div-div-37-->

   <!--RULE -->
   <xsl:template match="tei:div" priority="1000" mode="M39">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:div"/>
      <xsl:apply-templates select="*" mode="M39"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M39"/>
   <xsl:template match="@*|node()" priority="-2" mode="M39">
      <xsl:apply-templates select="*" mode="M39"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-div-abstractModel-structure-l-38-->

   <!--RULE -->
   <xsl:template match="tei:div" priority="1000" mode="M40">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:div"/>
      <!--REPORT -->
      <xsl:if test="ancestor::tei:l">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl" test="ancestor::tei:l">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>
        Abstract model violation: Lines may not contain higher-level structural elements such as div.
      </svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <xsl:apply-templates select="*" mode="M40"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M40"/>
   <xsl:template match="@*|node()" priority="-2" mode="M40">
      <xsl:apply-templates select="*" mode="M40"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-div-abstractModel-structure-p-39-->

   <!--RULE -->
   <xsl:template match="tei:div" priority="1000" mode="M41">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:div"/>
      <!--REPORT -->
      <xsl:if test="ancestor::tei:p or ancestor::tei:ab and not(ancestor::tei:floatingText)">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                 test="ancestor::tei:p or ancestor::tei:ab and not(ancestor::tei:floatingText)">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>
        Abstract model violation: p and ab may not contain higher-level structural elements such as div.
      </svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <xsl:apply-templates select="*" mode="M41"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M41"/>
   <xsl:template match="@*|node()" priority="-2" mode="M41">
      <xsl:apply-templates select="*" mode="M41"/>
   </xsl:template>
   <!--PATTERN isoschematron-constraint-dharma-ex-ex-40-->

   <!--RULE -->
   <xsl:template match="tei:ex" priority="1000" mode="M42">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:ex"/>
      <!--REPORT -->
      <xsl:if test="not(ancestor::tei:expan)">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl" test="not(ancestor::tei:expan)">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>ex should only appear inside
                            expan</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <!--REPORT -->
      <xsl:if test="parent::tei:abbr">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl" test="parent::tei:abbr">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>ex should not be a
                            child of abbr</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <xsl:apply-templates select="*" mode="M42"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M42"/>
   <xsl:template match="@*|node()" priority="-2" mode="M42">
      <xsl:apply-templates select="*" mode="M42"/>
   </xsl:template>
   <!--PATTERN isoschematron-constraint-dharma-am-ex-42-->

   <!--RULE -->
   <xsl:template match="tei:am" priority="1000" mode="M44">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:am"/>
      <!--REPORT -->
      <xsl:if test="not(ancestor::tei:abbr)">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl" test="not(ancestor::tei:abbr)">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>am should only appear inside
                            abbr</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <xsl:apply-templates select="*" mode="M44"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M44"/>
   <xsl:template match="@*|node()" priority="-2" mode="M44">
      <xsl:apply-templates select="*" mode="M44"/>
   </xsl:template>
   <!--PATTERN isoschematron-constraint-dharma-space-space-43-->

   <!--RULE -->
   <xsl:template match="tei:space" priority="1002" mode="M45">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:space"/>
      <!--REPORT -->
      <xsl:if test="@quantity and not(@unit)">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl" test="@quantity and not(@unit)">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>If space has @quantity then @unit is
                            required</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <xsl:apply-templates select="*" mode="M45"/>
   </xsl:template>
   <!--RULE -->
   <xsl:template match="tei:space" priority="1001" mode="M45">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:space"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="@type='binding-hole' or @type='descender' or @type='ascender' and @quantity and @unit"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                test="@type='binding-hole' or @type='descender' or @type='ascender' and @quantity and @unit">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>Space can't have @quantity and @unit attributes with
                            @type='binding-hole' or @type='descender' or @type='ascender', the only
                            @type possible is @type='defect'.</svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M45"/>
   </xsl:template>
   <!--RULE -->
   <xsl:template match="tei:space" priority="1000" mode="M45">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:space"/>
      <!--REPORT -->
      <xsl:if test="@unit='page'">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl" test="@unit='page'">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>Please note that the
                            use of "space" for blank copperplate pages has been discarded; encode
                            only a "pb" for the blank page</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <xsl:apply-templates select="*" mode="M45"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M45"/>
   <xsl:template match="@*|node()" priority="-2" mode="M45">
      <xsl:apply-templates select="*" mode="M45"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-subst-substContents1-44-->

   <!--RULE -->
   <xsl:template match="tei:subst" priority="1000" mode="M46">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:subst"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="child::tei:add and child::tei:del"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                test="child::tei:add and child::tei:del">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>
                  <xsl:text/>
                  <xsl:value-of select="name(.)"/>
                  <xsl:text/> must have at least one child add and at least one child del</svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M46"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M46"/>
   <xsl:template match="@*|node()" priority="-2" mode="M46">
      <xsl:apply-templates select="*" mode="M46"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-certainty-usage-certainty-45-->

   <!--RULE -->
   <xsl:template match="tei:certainty" priority="1003" mode="M47">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:certainty"/>
      <!--REPORT -->
      <xsl:if test="@match='../@met' and not(parent::tei:lg)">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                 test="@match='../@met' and not(parent::tei:lg)">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>The pattern used in
                            @match works with the element lg[@met]</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <xsl:apply-templates select="*" mode="M47"/>
   </xsl:template>
   <!--RULE -->
   <xsl:template match="tei:certainty" priority="1002" mode="M47">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:certainty"/>
      <!--REPORT -->
      <xsl:if test="@match='..' and not(parent::tei:gap)">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                 test="@match='..' and not(parent::tei:gap)">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>The pattern used in @match
                            works within the element gap</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <xsl:apply-templates select="*" mode="M47"/>
   </xsl:template>
   <!--RULE -->
   <xsl:template match="tei:certainty" priority="1001" mode="M47">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:certainty"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="@match='../@met' and @locus='value'"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                test="@match='../@met' and @locus='value'">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text> @match="../@met" and
                            @locus="value" always work together. </svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M47"/>
   </xsl:template>
   <!--RULE -->
   <xsl:template match="tei:certainty" priority="1000" mode="M47">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:certainty"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="@match='..' and @locus='name'"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                test="@match='..' and @locus='name'">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>@match='..' and @locus='name' always work
                            together</svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M47"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M47"/>
   <xsl:template match="@*|node()" priority="-2" mode="M47">
      <xsl:apply-templates select="*" mode="M47"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-ab-abstractModel-structure-ab-46-->

   <!--RULE -->
   <xsl:template match="tei:ab" priority="1000" mode="M48">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:ab"/>
      <!--REPORT -->
      <xsl:if test="not(ancestor::tei:floatingText) and (ancestor::tei:p or ancestor::tei:ab)          and not(parent::tei:exemplum         |parent::tei:item         |parent::tei:note         |parent::tei:q         |parent::tei:quote         |parent::tei:remarks         |parent::tei:said         |parent::tei:sp         |parent::tei:stage         |parent::tei:cell         |parent::tei:figure)">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                 test="not(ancestor::tei:floatingText) and (ancestor::tei:p or ancestor::tei:ab) and not(parent::tei:exemplum |parent::tei:item |parent::tei:note |parent::tei:q |parent::tei:quote |parent::tei:remarks |parent::tei:said |parent::tei:sp |parent::tei:stage |parent::tei:cell |parent::tei:figure)">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>
        Abstract model violation: ab may not occur inside paragraphs or other ab elements.
      </svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <xsl:apply-templates select="*" mode="M48"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M48"/>
   <xsl:template match="@*|node()" priority="-2" mode="M48">
      <xsl:apply-templates select="*" mode="M48"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-ab-abstractModel-structure-l-47-->

   <!--RULE -->
   <xsl:template match="tei:ab" priority="1000" mode="M49">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:ab"/>
      <!--REPORT -->
      <xsl:if test="ancestor::tei:l or ancestor::tei:lg">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                 test="ancestor::tei:l or ancestor::tei:lg">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>
        Abstract model violation: Lines may not contain higher-level divisions such as p or ab.
      </svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <xsl:apply-templates select="*" mode="M49"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M49"/>
   <xsl:template match="@*|node()" priority="-2" mode="M49">
      <xsl:apply-templates select="*" mode="M49"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-seg-att-type-subtype-48-->

   <!--RULE -->
   <xsl:template match="tei:seg" priority="1000" mode="M50">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:seg"/>
      <!--REPORT -->
      <xsl:if test="@subtype and not(@type='component')">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                 test="@subtype and not(@type='component')">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>@subtype requires
                            @type='component' to be used</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <!--REPORT -->
      <xsl:if test="@cert='low' and not(ancestor::tei:div[@type='translation'])">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                 test="@cert='low' and not(ancestor::tei:div[@type='translation'])">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>seg[@cert='low'] can be used only in
                            div[@type='translation']</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <!--REPORT -->
      <xsl:if test="@rend='pun' and not(ancestor::tei:div[@type='translation'])">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                 test="@rend='pun' and not(ancestor::tei:div[@type='translation'])">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>seg[@rend='pun'] only avaailable in
                            div[@type='translation']</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <xsl:apply-templates select="*" mode="M50"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M50"/>
   <xsl:template match="@*|node()" priority="-2" mode="M50">
      <xsl:apply-templates select="*" mode="M50"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-dimensions-duplicateDim-49-->

   <!--RULE -->
   <xsl:template match="tei:dimensions" priority="1000" mode="M51">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:dimensions"/>
      <!--REPORT -->
      <xsl:if test="count(tei:width)&gt; 1">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl" test="count(tei:width)&gt; 1">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>
The element <xsl:text/>
               <xsl:value-of select="name(.)"/>
               <xsl:text/> may appear once only
      </svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <!--REPORT -->
      <xsl:if test="count(tei:height)&gt; 1">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl" test="count(tei:height)&gt; 1">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>
The element <xsl:text/>
               <xsl:value-of select="name(.)"/>
               <xsl:text/> may appear once only
      </svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <!--REPORT -->
      <xsl:if test="count(tei:depth)&gt; 1">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl" test="count(tei:depth)&gt; 1">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>
The element <xsl:text/>
               <xsl:value-of select="name(.)"/>
               <xsl:text/> may appear once only
      </svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <xsl:apply-templates select="*" mode="M51"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M51"/>
   <xsl:template match="@*|node()" priority="-2" mode="M51">
      <xsl:apply-templates select="*" mode="M51"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-origDate-origDate-50-->

   <!--RULE -->
   <xsl:template match="tei:origDate[ancestor::tei:teiHeader]"
                 priority="1000"
                 mode="M52">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                       context="tei:origDate[ancestor::tei:teiHeader]"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="@when or (@notBefore and @notAfter) or (@from and @to)"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                test="@when or (@notBefore and @notAfter) or (@from and @to)">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>The content of the element date should be translated into the W3C format thanks to @when or (@notBefore and @notAfter) or (@from and @to)</svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M52"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M52"/>
   <xsl:template match="@*|node()" priority="-2" mode="M52">
      <xsl:apply-templates select="*" mode="M52"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-signatures-signatures_in_msDesc-51-->

   <!--RULE -->
   <xsl:template match="tei:signatures" priority="1000" mode="M53">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:signatures"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="ancestor::tei:msDesc or ancestor::tei:egXML"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                test="ancestor::tei:msDesc or ancestor::tei:egXML">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>The <xsl:text/>
                  <xsl:value-of select="name(.)"/>
                  <xsl:text/> element should not be used outside of msDesc.</svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M53"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M53"/>
   <xsl:template match="@*|node()" priority="-2" mode="M53">
      <xsl:apply-templates select="*" mode="M53"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-msIdentifier-msId_minimal-52-->

   <!--RULE -->
   <xsl:template match="tei:msIdentifier" priority="1000" mode="M54">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:msIdentifier"/>
      <!--REPORT -->
      <xsl:if test="not(parent::tei:msPart) and (local-name(*[1])='idno' or local-name(*[1])='altIdentifier' or normalize-space(.)='')">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                 test="not(parent::tei:msPart) and (local-name(*[1])='idno' or local-name(*[1])='altIdentifier' or normalize-space(.)='')">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>An msIdentifier must contain either a repository or location.</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <xsl:apply-templates select="*" mode="M54"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M54"/>
   <xsl:template match="@*|node()" priority="-2" mode="M54">
      <xsl:apply-templates select="*" mode="M54"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-persName-reference-53-->

   <!--RULE -->
   <xsl:template match="tei:persName/@ref[ancestor::tei:teiHeader]"
                 priority="1000"
                 mode="M55">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                       context="tei:persName/@ref[ancestor::tei:teiHeader]"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="starts-with(.,'part:') or starts-with(.,'http')"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                test="starts-with(.,'part:') or starts-with(.,'http')">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>Project members prefix is part: et non-members should be a
                            URL</svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M55"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M55"/>
   <xsl:template match="@*|node()" priority="-2" mode="M55">
      <xsl:apply-templates select="*" mode="M55"/>
   </xsl:template>
   <!--PATTERN isoschematron-constraint-dharma-placeName-div-54-->

   <!--RULE -->
   <xsl:template match="tei:placeName[@type='region']" priority="1006" mode="M56">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                       context="tei:placeName[@type='region']"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="@subtype='district' or @subtype='province' or @subtype='country' or @subtype='undetermined' or @subtype='land' or @subtype='island'"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                test="@subtype='district' or @subtype='province' or @subtype='country' or @subtype='undetermined' or @subtype='land' or @subtype='island'">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>For @type="region", the @subtype should be one of the
                            following values: @subtype='district' or @subtype='province' or @subtype='country' or @subtype='undetermined' or @subtype='land' or @subtype='island'</svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M56"/>
   </xsl:template>
   <!--RULE -->
   <xsl:template match="tei:placeName[@type='settlement']"
                 priority="1005"
                 mode="M56">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                       context="tei:placeName[@type='settlement']"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="@subtype='town' or @subtype='village' or @subtype='hamlet' or @subtype='armyCamp' or @subtype='undetermined' or @subtype='establishment'"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                test="@subtype='town' or @subtype='village' or @subtype='hamlet' or @subtype='armyCamp' or @subtype='undetermined' or @subtype='establishment'">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>For @type="settlement", the @subtype should be one of the
                                following values: @subtype='town' or @subtype='village' or @subtype='hamlet' or @subtype='armyCamp' or @subtype='undetermined' or @subtype='establishment'</svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M56"/>
   </xsl:template>
   <!--RULE -->
   <xsl:template match="tei:placeName[@type='builtPlace']"
                 priority="1004"
                 mode="M56">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                       context="tei:placeName[@type='builtPlace']"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="@subtype='temple' or @subtype='monastery' or @subtype='feedingHall' or @subtype='pavillion' or @subtype='undetermined'"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                test="@subtype='temple' or @subtype='monastery' or @subtype='feedingHall' or @subtype='pavillion' or @subtype='undetermined'">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>For @type="builtPlace", the @subtype should be one of the following
                                values: @subtype='temple' or @subtype='monastery' or @subtype='feedingHall' or @subtype='pavillion' or @subtype='undetermined'</svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M56"/>
   </xsl:template>
   <!--RULE -->
   <xsl:template match="tei:placeName[@type='cultivation']"
                 priority="1003"
                 mode="M56">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                       context="tei:placeName[@type='cultivation']"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="@subtype='garden' or @subtype='field' or @subtype='fieldPaddy' or @subtype='fieldMillet' or @subtype='orchard' or @subtype='orchardAreca' or @subtype='orchardCitrus' or @subtype='fieldIrrigated' or @subtype='fieldDry' or @subtype='fieldSalted' or @subtype='undetermined' or @subtype='nursery'"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                test="@subtype='garden' or @subtype='field' or @subtype='fieldPaddy' or @subtype='fieldMillet' or @subtype='orchard' or @subtype='orchardAreca' or @subtype='orchardCitrus' or @subtype='fieldIrrigated' or @subtype='fieldDry' or @subtype='fieldSalted' or @subtype='undetermined' or @subtype='nursery'">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>For @type="cultivation", the @subtype should be one of the following
                                values: @subtype='garden' or @subtype='field' or @subtype='fieldPaddy' or @subtype='fieldMillet' or @subtype='orchard' or @subtype='orchardAreca' or @subtype='orchardCitrus' or @subtype='fieldIrrigated' or @subtype='fieldDry' or @subtype='fieldSalted' or @subtype='undetermined' or @subtype='nursery'</svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M56"/>
   </xsl:template>
   <!--RULE -->
   <xsl:template match="tei:placeName[@type='hydrographic']"
                 priority="1002"
                 mode="M56">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                       context="tei:placeName[@type='hydrographic']"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="@subtype='tank' or @subtype='river' or @subtype='pond' or @subtype='canal' or @subtype='undetermined' or @subtype='wetland' or @sutype='pool' or @subtype='lake'"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                test="@subtype='tank' or @subtype='river' or @subtype='pond' or @subtype='canal' or @subtype='undetermined' or @subtype='wetland' or @sutype='pool' or @subtype='lake'">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>For @type="hydrographic", the @subtype should be one of the following
                                values: @subtype='tank' or @subtype='river' or @subtype='pond' or @subtype='canal' or @subtype='undetermined' or @subtype='wetland' or @sutype='pool' or @subtype='lake'</svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M56"/>
   </xsl:template>
   <!--RULE -->
   <xsl:template match="tei:placeName[@type='naturalPlace']"
                 priority="1001"
                 mode="M56">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                       context="tei:placeName[@type='naturalPlace']"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="@subtype='forest' or @subtype='wood' or @subtype='grove' or @subtype='tree' or @subtype='mountain' or @subtype='undetermined' or @subtype='mount'"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                test="@subtype='forest' or @subtype='wood' or @subtype='grove' or @subtype='tree' or @subtype='mountain' or @subtype='undetermined' or @subtype='mount'">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>For @type="naturalPlace", the @subtype should be one of the following
                                values: @subtype='forest' or @subtype='wood' or @subtype='grove' or @subtype='tree' or @subtype='mountain' or @subtype='undetermined' or @subtype='mount'</svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M56"/>
   </xsl:template>
   <!--RULE -->
   <xsl:template match="tei:placeName[@type='undetermined']"
                 priority="1000"
                 mode="M56">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                       context="tei:placeName[@type='undetermined']"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="not(@subtype)"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl" test="not(@subtype)">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>@subtype isn't allowed with @type='undetermined'</svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M56"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M56"/>
   <xsl:template match="@*|node()" priority="-2" mode="M56">
      <xsl:apply-templates select="*" mode="M56"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-objectIdentifier-objectIdentifier_minimal-55-->

   <!--RULE -->
   <xsl:template match="tei:objectIdentifier" priority="1000" mode="M57">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:objectIdentifier"/>
      <!--REPORT -->
      <xsl:if test="not(count(*) gt 0)">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl" test="not(count(*) gt 0)">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>An objectIdentifier must contain at minimum a single piece of locating or identifying information.</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <xsl:apply-templates select="*" mode="M57"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M57"/>
   <xsl:template match="@*|node()" priority="-2" mode="M57">
      <xsl:apply-templates select="*" mode="M57"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-app-one-lem-56-->

   <!--RULE -->
   <xsl:template match="tei:app" priority="1000" mode="M58">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:app"/>
      <!--REPORT -->
      <xsl:if test="not(count(child::tei:lem) &gt;= 1)">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                 test="not(count(child::tei:lem) &gt;= 1)">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>An apparatus entry must always
                            contain a lem element</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <!--REPORT -->
      <xsl:if test="count(child::tei:lem) eq 1 and not(child::tei:lem[@source]) and not(child::tei:rdg or child::tei:note)">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                 test="count(child::tei:lem) eq 1 and not(child::tei:lem[@source]) and not(child::tei:rdg or child::tei:note)">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>When the apparatus entry contains only a lem, the @source is
                            mandatory</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <xsl:apply-templates select="*" mode="M58"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M58"/>
   <xsl:template match="@*|node()" priority="-2" mode="M58">
      <xsl:apply-templates select="*" mode="M58"/>
   </xsl:template>
   <!--PATTERN isoschematron-constraint-dharma-listApp-div-57-->

   <!--RULE -->
   <xsl:template match="tei:listApp" priority="1000" mode="M59">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:listApp"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="ancestor::tei:div[@type='apparatus']"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                test="ancestor::tei:div[@type='apparatus']">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>ListApp can only be used
                            inside the apparatus.</svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M59"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M59"/>
   <xsl:template match="@*|node()" priority="-2" mode="M59">
      <xsl:apply-templates select="*" mode="M59"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-lem-exclusion-inside-lem-58-->

   <!--RULE -->
   <xsl:template match="tei:lem" priority="1000" mode="M60">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:lem"/>
      <!--REPORT -->
      <xsl:if test="child::tei:p">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl" test="child::tei:p">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>The
                            element p is not allowed in lem</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <!--REPORT -->
      <xsl:if test="child::tei:ab">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl" test="child::tei:ab">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>The element ab is not allowed in
                            lem</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <!--REPORT -->
      <xsl:if test="child::tei:lg">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl" test="child::tei:lg">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>The element lg is not
                            allowed in lem</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <!--REPORT -->
      <xsl:if test="count(child::tei:l) eq 1">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl" test="count(child::tei:l) eq 1">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>Don't keep the l element in lem if you have only one of them</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <xsl:apply-templates select="*" mode="M60"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M60"/>
   <xsl:template match="@*|node()" priority="-2" mode="M60">
      <xsl:apply-templates select="*" mode="M60"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-rdg-exclusion-inside-lem-59-->

   <!--RULE -->
   <xsl:template match="tei:rdg" priority="1000" mode="M61">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:rdg"/>
      <!--REPORT -->
      <xsl:if test="child::tei:p">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl" test="child::tei:p">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>The
                            element p is not allowed in rdg</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <!--REPORT -->
      <xsl:if test="child::tei:ab">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl" test="child::tei:ab">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>The element ab is not allowed in
                            rdg</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <!--REPORT -->
      <xsl:if test="child::tei:lg">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl" test="child::tei:lg">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>The element lg is not
                            allowed in rdg</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <!--REPORT -->
      <xsl:if test="child::tei:l">
         <svrl:successful-report xmlns:svrl="http://purl.oclc.org/dsdl/svrl" test="child::tei:l">
            <xsl:attribute name="location">
               <xsl:apply-templates select="." mode="schematron-select-full-path"/>
            </xsl:attribute>
            <svrl:text>The element l
                            is not allowed in rdg</svrl:text>
         </svrl:successful-report>
      </xsl:if>
      <xsl:apply-templates select="*" mode="M61"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M61"/>
   <xsl:template match="@*|node()" priority="-2" mode="M61">
      <xsl:apply-templates select="*" mode="M61"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-rdgGrp-only1lem-60-->

   <!--RULE -->
   <xsl:template match="tei:rdgGrp" priority="1000" mode="M62">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:rdgGrp"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="count(tei:lem) &lt; 2"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl" test="count(tei:lem) &lt; 2">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>Only one &lt;lem&gt; element may appear within a &lt;rdgGrp&gt;</svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M62"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M62"/>
   <xsl:template match="@*|node()" priority="-2" mode="M62">
      <xsl:apply-templates select="*" mode="M62"/>
   </xsl:template>
   <!--PATTERN schematron-constraint-dharma-variantEncoding-location-variantEncodingLocation-61-->

   <!--RULE -->
   <xsl:template match="tei:variantEncoding" priority="1000" mode="M63">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl" context="tei:variantEncoding"/>
      <!--ASSERT -->
      <xsl:choose>
         <xsl:when test="(@location != 'external') or (@method != 'parallel-segmentation')"/>
         <xsl:otherwise>
            <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                                test="(@location != 'external') or (@method != 'parallel-segmentation')">
               <xsl:attribute name="location">
                  <xsl:apply-templates select="." mode="schematron-select-full-path"/>
               </xsl:attribute>
               <svrl:text>
              The @location value "external" is inconsistent with the
              parallel-segmentation method of apparatus markup.</svrl:text>
            </svrl:failed-assert>
         </xsl:otherwise>
      </xsl:choose>
      <xsl:apply-templates select="*" mode="M63"/>
   </xsl:template>
   <xsl:template match="text()" priority="-1" mode="M63"/>
   <xsl:template match="@*|node()" priority="-2" mode="M63">
      <xsl:apply-templates select="*" mode="M63"/>
   </xsl:template>
</xsl:stylesheet>
