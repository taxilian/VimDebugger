<?php

/*
 * This file is here for convenience; the actual functions used by the debugger 
 * are in VimDebugger.py at the bottom
 */

function __xdbg_get_value($var, $maxDepth=2) {
    $return = null;
    $isObj = is_object($var);

    if ($isObj && in_array("Doctrine\Common\Collections\Collection", class_implements($var))) {
        $var = $var->toArray();
    }
    
    if ($maxDepth > 0) {
        if (is_array($var)) {
            $return = array();
        
            foreach ($var as $k => $v) {
                $return[$k] = __xdbg_get_value($v, $maxDepth - 1);
            }
        } else if ($isObj) {
            if ($var instanceof \DateTime) {
                $return = $var->format("c");
            } else {
                $reflClass = new \ReflectionClass(get_class($var));
                $return = new \stdclass();
                $return->{"__CLASS__"} = get_class($var);

                if (is_a($var, "Doctrine\\ORM\\Proxy\\Proxy") && ! $var->__isInitialized__) {
                    $reflProperty = $reflClass->getProperty("_identifier");
                    $reflProperty->setAccessible(true);

                    foreach ($reflProperty->getValue($var) as $name => $value) {
                        $return->$name = __xdbg_get_value($value, $maxDepth - 1);
                    }
                } else {
                    $excludeProperties = array();

                    if (is_a($var, "Doctrine\\ORM\\Proxy\\Proxy")) {
                        $excludeProperties = array("_entityPersister", "__isInitialized__", "_identifier");

                        foreach ($reflClass->getProperties() as $reflProperty) {
                            $name  = $reflProperty->getName();

                            if ( ! in_array($name, $excludeProperties)) {
                                $reflProperty->setAccessible(true);

                                $return->$name = __xdbg_get_value($reflProperty->getValue($var), $maxDepth - 1);
                            }
                        }
                    } else {
                        $return = $var;
                    }
                }
                $return = __xdbg_get_object($return, $maxDepth-1);
            }
        } else {
            $return = $var;
        }
    } else {
        $return = is_object($var) ? get_class($var) 
            : (is_array($var) ? "Array(" . count($var) . ")" : $var);
    }
    
    return $return;
}

function __xdbg_get_propertyList($propList, $item, $maxDepth=2) {
    $output = array();
    foreach ($propList as $prop) {
        $static = $prop->isStatic() ? "static " : "";
        $vis = $prop->isProtected() ? "protected" : $prop->isPrivate() ? "private" : "public";
        $name = $prop->getName();
        $val = null;
        if (!$prop->isPublic()) {
            $prop->setAccessible(true);
            $val = $prop->getValue($item);
            $prop->setAccessible(false);
        } else {
            $val = $prop->getValue($item);
        }
        $desc = $static."$vis \$$name";
        $output[$desc] = __xdbg_get_value($val, $maxDepth);
    }
    return $output;
}

function __xdbg_get_methodList($methodList) {
    $output = array();
    foreach ($methodList as $method) {
        $static = $method->isStatic() ? "static " : "";
        $vis = $method->isPrivate() ? "private" : $method->isProtected() ? "protected" : "public";
        $name = $method->getName();
        $params = array();
        $plist = $method->getParameters();
        foreach ($plist as $param) {
            $params[] = "$" . $param->getName();
        }
        $desc = $static."$vis $name(" . implode(", ", $params) . ")";
        $output[] = $desc;
    }
    return $output;
}

function __xdbg_get_object($var, $maxDepth=2) {
    $entry = array();
    $class = get_class($var);
    $ref = new ReflectionClass($var);
    $entry = array(
        "properties" => __xdbg_get_propertyList($ref->getProperties(), $var, $maxDepth-1),
        "methods" => __xdbg_get_methodList($ref->getMethods()),
        "className" => $class,
        "isClass" => true,
    );
    return $entry;
}

function __xdbg_get_objList(array $listx2) {
    $outputFull = array();
    foreach ($listx2 as $list) {
        $output = array();
        foreach ($list as $item) {
            $output[] = __xdbg_get_value($item);
        }
        $outputFull[] = $output;
    }
    return @json_encode($outputFull);
}

function __xdbg_run($method) { ob_start(); $method(); $tmp = ob_get_contents(); ob_end_clean(); return $tmp; }
