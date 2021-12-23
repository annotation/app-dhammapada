import sys

from tf.convert.recorder import Recorder


def makeLegends(maker):
    pass


def record(maker):
    A = maker.A

    api = A.api
    F = api.F
    Fs = api.Fs
    L = api.L

    C = maker.C
    layerSettings = C.layerSettings

    clientConfig = maker.clientConfig
    typesLower = clientConfig["typesLower"]

    A.indent(reset=True)
    A.info("preparing ... ")

    A.info("start recording")

    up = {}
    recorders = {}
    accumulators = {}
    maker.up = up
    maker.recorders = recorders
    maker.accumulators = accumulators

    for (level, typeInfo) in layerSettings.items():
        ti = typeInfo.get("layers", None)
        if ti is None:
            continue

        recorders[level] = {
            layer: Recorder(api) for layer in ti if ti[layer]["pos"] is None
        }
        accumulators[level] = {layer: [] for layer in ti if ti[layer]["pos"] is not None}

    def addValue(node, use=None):
        returnValue = None

        level = use or F.otype.v(node)
        typeInfo = layerSettings[level]
        theseLayers = typeInfo.get("layers", {})

        first = True

        for layer in theseLayers:
            info = theseLayers[layer]
            descend = info.get("descend", False)
            ascend = info.get("ascend", False)
            feature = info.get("feature", None)
            beforeFeature = info.get("beforeFeature", None)
            afterFeature = info.get("afterFeature", None)
            afterDefault = info.get("afterDefault", None)
            vMap = info.get("legend", None)
            if type(vMap) is not dict:
                vMap = None
            default = info["default"]
            pos = info["pos"]

            beforeFunc = Fs(beforeFeature).v if beforeFeature else lambda x: ""
            afterFunc = Fs(afterFeature).v if afterFeature else lambda x: ""
            materialFunc = Fs(feature).v

            if descend:
                value = ""
                for n in L.d(node, otype=descend):
                    val = materialFunc(n)
                    if vMap:
                        val = vMap.get(val, default)
                    else:
                        val = val or default

                    value += f"{beforeFunc(n) or ''}{val}{afterFunc(n) or ''}"
            else:
                refNode = L.u(node, otype=ascend)[0] if ascend else node
                value = materialFunc(refNode)
                if vMap:
                    value = vMap.get(value, default)
                else:
                    value = value or default

                value = f"{beforeFunc(refNode) or ''}{value}{afterFunc(refNode) or ''}"

            afterVal = "" if afterDefault is None else afterDefault
            value = f"{value}{afterVal}"

            if pos is None:
                recorders[level][layer].add(value)
            else:
                accumulators[level][layer].append(value)

            if first:
                returnValue = value
                first = False

        return returnValue

    def addAfterValue(node):
        level = F.otype.v(node)
        typeInfo = layerSettings[level]
        value = typeInfo.get("afterDefault", None)
        if value:
            addLevel(level, value)

    def addAll(level, value):
        lowerTypes = typesLower[level]
        for lType in lowerTypes:
            if lType in recorders:
                for x in recorders[lType].values():
                    x.add(value)
            if lType in accumulators:
                for x in accumulators[lType].values():
                    x.append(value)

    def addLevel(level, value):
        if level in recorders:
            for x in recorders[level].values():
                x.add(value)
        if level in accumulators:
            for x in accumulators[level].values():
                x.append(value)

    def addLayer(level, layer, value):
        if level in recorders:
            if layer in recorders[level]:
                recorders[level][layer].add(value)
        if level in accumulators:
            if layer in accumulators[level]:
                accumulators[level][layer].append(value)

    def startNode(node, asType=None):
        # we have organized recorders by node type
        # we only record nodes of matching type in recorders

        level = asType or F.otype.v(node)

        if level in recorders:
            for rec in recorders[level].values():
                rec.start(node)

    def endNode(node, asType=None):
        # we have organized recorders by node type
        # we only record nodes of matching type in recorders
        level = asType or F.otype.v(node)

        if level in recorders:
            for rec in recorders[level].values():
                rec.end(node)

    # note the `up[n] = m` statements below:
    # we only let `up` connect nodes from one level to one level higher

    for (i, vagga) in enumerate(F.otype.s("vagga")):
        startNode(vagga)
        title = addValue(vagga)
        sys.stdout.write("\r" + f"vagga {title}")

        for stanza in L.d(vagga, otype="stanza"):
            up[stanza] = vagga
            startNode(stanza)
            addValue(stanza)

            for word in L.d(stanza, otype="word"):
                up[word] = stanza
                startNode(word)
                addValue(word)
                endNode(word)

            addAfterValue(stanza)
            endNode(stanza)
        addAfterValue(vagga)
        endNode(vagga)

    sys.stdout.write("\n")
    A.info("done")
