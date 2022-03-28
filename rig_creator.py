"""
#######################################
filename    rig_creator.py
author      Owen McCubbin
dP email    owen.mccubbin@digipen.edu
personal email   mccubbinowen@gmail.com
course      PRJ450
Brief Description:
    Use this tool to create a basic rig for characters in housini,
    capture the skin weights of the character using Biharmonic
    and if desired create deforms that will allow for the creation of different shaped characters based off of the original.
#######################################
"""

## PLEASE PASTE YOUR SCRIPT FOLDER BELOW
script_folder = 'C:\Users\mccub\OneDrive\Documents\houdini18.0\Full_Rig'
"""
import sys
if script_folder not in sys.path:
    sys.path.append(script_folder)
import rig_creator
reload(rig_creator)
rig_creator.run()
"""



##import needed packages
import hou
import math
import os
from past.utils import old_div

from PySide2 import QtCore
from PySide2 import QtWidgets
from PySide2 import QtUiTools

from rigtoolutils import rigutils
from rigtoolutils import iktwistnaming as naming
from rigtoolutils import iktwistcontrols as controls
from rigtoolutils import fkikinterfacecontrol as fkikinterface
from rigtoolutils import iktwistnetworkeditor as networkedit




def create_bone_nonOrient(node_0, node_1, parent, prefix):
    ##find net parent
    net_parent = node_0.parent()

    ##create root name for future root node
    #root_name = start_node.name() + '_root'
    #print root_name
    
    #root_null = net_parent.createNode('null', root_name)
    #root_null.setInput(0, start_node, 0)
    #root_null.parm('keeppos').set(1)
    #root_null.setInput(0,None,0)
    
    bone_name = prefix + '_bone1'
    
    ##determine the length/distance between the null objs for later bone length
    distance = (node_0.origin()-node_1.origin()).length()
    #print distance
    
    ##create the new bone node in the net_parent level
    newbone = net_parent.createNode('bone', bone_name)
    ##enable xray
    newbone.useXray(True)
    ##if the bone does not have a determined parent, ie 0, than place the bone at the start_node
    if parent == 0:
        ##parent the bone to the start_node for proper placement
        newbone.setInput(0, node_0, 0)
        ##Unparent the new bone with keep position
        newbone.parm('keeppos').set(1)
        newbone.setInput(0, None, 0)
    else:
        ##parent the new bone to the parent determined in the def call
        newbone.setInput(0, parent, 0)
    ##set the length to the distance determined earlier
    newbone.parm('length').set(distance)
    ##find the rotation needed for the bone to be pointed at the end_node
    newbone_lookat = newbone.buildLookatRotation(node_1)
    ##push that gather rotation info into the bone
    newbone.setParmTransform(newbone_lookat)
    ##get a random color and give it to the bone
    color = rigutils.getRandomColor()
    rigutils.setDisplayColor(newbone, color)
    ##layout the nodes in the node editor
    net_parent.layoutChildren()
    
    return newbone

##create a function capable of calculating the normal of a plane given 3 objects
def calculate_plane_normal(node_0, node_1, node_2):
    ##get the vector between the 1st and 2nd objects
    first_vector = node_1.origin() - node_0.origin()
    ##get the vector between the 2nd and 3rd object 
    second_vector = node_2.origin() - node_1.origin()
    ##get the cross product of the vectors and normalize it
    plane_normal = first_vector.cross(second_vector).normalized()
    
    ##return the desired plane normal vector
    return hou.Vector3(plane_normal[0], plane_normal[1], plane_normal[2])
    

def create_bone_in_chain(node_0, node_1, normal, bone_parent, prefix):
    
    ##create a new bone from the nonOrient def earlier
    newbone = create_bone_nonOrient(node_0, node_1, bone_parent, prefix)
    
    ##The rest of this def is highly influenced by a default houdini shelf tool 'IK from Objects'
    ##The python for said shelf tool can be found at  houdini instal directory/houdini/python2.7libs/rigtoolutils - see iktwisttool.py
    
    # The bones are not in a straight line and we can orient the bone
    if normal.length() != 0:
        bone_normal = hou.Vector4(1.0, 0.0, 0.0, 0.0)
        bone_world_orient = bone_normal * newbone.worldTransform()
        bone_world_orient_normal = hou.Vector3(bone_world_orient[0], bone_world_orient[1], bone_world_orient[2])
        bone_world_orient_normal = bone_world_orient_normal.normalized()

        plane_bone_dot = normal.dot(bone_world_orient_normal)
        cos_angle = old_div(plane_bone_dot, ( normal.length() * bone_world_orient_normal.length() ))
        cos_angle = max(-1, min(cos_angle, 1))
        rotate_angle = math.degrees(math.acos(cos_angle))

        plane_bone_orient_cross = (normal.cross(bone_world_orient_normal)).normalized()
        bone_vector = (node_1.origin() - node_0.origin()).normalized();
        plane_bone_orient_dot = bone_vector.dot(plane_bone_orient_cross)

        if plane_bone_orient_dot < 0:
            rotate_angle = -rotate_angle

        newbone.parm('rz').set(newbone.parm('rz').eval() + rotate_angle)
    
    newbone.moveParmTransformIntoPreTransform()
    rigutils.setAllRestAngles(newbone, 0)
    newbone.parm('keeppos').set(True)

    return newbone
    
    
def create_root_bone_chain(parent, objs, prefix):
    ##define the net parent level
    net_parent = objs[0].parent()
    
    """ Creates a bone chain such that the bones are positioned at the obj positions.
    The first two bones are oriented in the plane they make. The rest of the bones
    are oriented between the plane that it makes with the parent bone. If there is
    only one bone or the bones are in a straight line, the bones are oriented based
    on their parents

    Input:
        parent - parent of the created bone structure
        objs - list of objs to position the bones at (assumes to have length >= 2)
        prefix - prefix for the name of the bones
    """
    
    ##grab each node from the objs list
    node_0 = objs[0]
    node_1 = objs[1]
    
    
    ##determine a root name based of the prefix
    root_name = prefix + '_root'
    
    parent_name = prefix + '_parent'
    
    ##create a root null node at the point of node_0
    root = rigutils.createNullAtNode(net_parent, node_0, root_name)
    root.parm('geoscale').set(.02)
    root.parm('controltype').set(1)
    ##if there is no parent, create on at the node_0 location
    if parent == 0:
        #create null node at node_0
        parent = rigutils.createNullAtNode(net_parent, node_0, parent_name)
        #change the null's visual to be circles
        parent.parm('controltype').set(1)
        ##change the size of the displayed circles to be super small
        parent.parm('geoscale').set(0.02)
        """
        ##parent the bone to the start_node for proper placement
        root.setInput(0, node_0, 0)
        ##Unparent the new bone with keep position
        root.parm('keeppos').set(1)
        root.setInput(0, None, 0)
        """
    ##parent the root under the parent
    root.setFirstInput(parent)
    
    ##when the list of objs only has 2 items than create a bone nonOrient
    if len(objs) == 2:
        newbone = create_bone_nonOrient(node_0, node_1, root, prefix)
        return (root, newbone)
    
    node_2 = objs[2]
    
    ##calculate the plane normal of the 3 nodes
    plane_normal = calculate_plane_normal(node_0, node_1, node_2)
    
    ##create the first bone from node_0 to node_1
    last_bone = create_bone_in_chain(node_0, node_1, plane_normal, root, prefix)
    first_bone = last_bone
    
    ##createing bones after firstbone
    for i, item in enumerate(objs[2:]):
        ##set the new node_0 to be i (which the first i would be 2)
        node_0 = objs[i]
        ##set the new node_1 to be i+
        node_1 = objs[i+1]
        ##set node_2 to be item
        node_2 = item
        ##determie the new plane normal for the new 3 nodes
        plane_normal = calculate_plane_normal(node_0, node_1, node_2)
        ##create a new bone and parent it to the last_bone
        last_bone = create_bone_in_chain(node_1, node_2, plane_normal, last_bone, prefix)
        
    return (root, first_bone, last_bone)
    
def rigutils_create_IK_FK(IK_type, start_bone, end_bone, parent, prefix):
    """IK_type should be 0 or 1, 0 = basic, 1 = twist"""
    
    ##get the level type from the parent
    net_parent = parent.parent()
    
    prefix = prefix + '_'
    
    created_controls = controls.createControlsWithBones(IK_type, start_bone, end_bone, parent, net_parent, prefix)
    
    created_controls['interface'] = fkikinterface.createIKFKInterface(net_parent, start_bone.inputs()[0], prefix, 
                                                                      endaffectorpath = created_controls['endhook'].path(),
                                                                      twistaffectorpath = (created_controls['twisthook'].path() if IK_type == 1 else ''),
                                                                      startbonepath = start_bone.path(),
                                                                      endbonepath = end_bone.path(),
                                                                      kinsolverpath = created_controls['iksolver'].path())
    ##create extra information for hiding and organizing the created joints and controls
    created_controls['startbone'] = start_bone
    created_controls['endbone'] = end_bone
    created_controls['root'] = start_bone.inputs()[0]
    created_controls['parent'] = parent
    created_controls['ikortwist'] = IK_type
    created_controls['prefix'] = prefix
    created_controls['netparent'] = net_parent
    created_controls['selectedparent'] = True
    
    ##use the created data to hide and organize the new nodes
    networkedit.hideAndOrganizeCreatedObjs(created_controls)

##def for easily creating null nodes with a conection to another null node
##required inputs: net_parent = the network to make the node in,
    ##pointer_node = the node to connect to
    ##name = name of this new node must be str
def create_null_pointer(net_parent, pointer_node, name):
    ##create a new null node in the network
    null_pointer = net_parent.createNode('null', name)
    ##change the null size and display
    null_pointer.parm('geoscale').set(.25)
    null_pointer.parm('controltype').set(4)
    ##create a name for the obj merge in the node
    pointer_merge_name = pointer_node.name() + '_point_merge'
    ##create the object merge node
    point_merge = null_pointer.createNode('object_merge', pointer_merge_name)
    ##create a path to the desired point of the node to connect to
    point_node = pointer_node.path() + '/point1'
    ##set parameters of object merge node to bring in the point
    point_merge.parm('objpath1').set(point_node)
    point_merge.parm('xformtype').set(1)
    ##create a merge node
    merge = null_pointer.createNode('merge', 'merge_points')
    ##grab the point from within the node that gets created in this function
    internal_point = net_parent.path() + '/' + name + '/point1'
    internal_point = hou.node(internal_point)
    ##set the merge nodes inputs
    merge.setInput(0, internal_point, 0)
    merge.setInput(1, point_merge, 0)
    ##create a node that will make the line
    line = null_pointer.createNode('add', 'connection_line')
    ##parent the line under the merge
    line.setFirstInput(merge)
    ##switch the tab type from "By Pattern" to "By Group"
    line.parm('switcher1').set(1)
    ##create a merge for the line and the control visual
    display_merge = null_pointer.createNode('merge', 'merge_display')
    ##grab internal control node
    internal_control = net_parent.path() + '/' + name + '/control1'
    internal_control = hou.node(internal_control)
    ##set display merge inputs
    display_merge.setInput(0, internal_control, 0)
    display_merge.setInput(1, line, 0)
    ##set display flags
    display_merge.setRenderFlag(True)
    display_merge.setDisplayFlag(True)
    ##return the node
    return (null_pointer)

def split_bone(bone, split_num):
    ##get the net parent
    net_parent = bone.parent()
    ##get the name of the bone to split
    name = bone.name()
    ##get the parent of the bone node
    parent = bone.inputs()[0]
    ##get the bone length
    bone_length = bone.parm('length').eval()
    ##devide that length by how many times you are going to split
    split_length = bone_length/int(split_num)
    ##create a bone for however many times you want to split
    for num in range(0, split_num):
        ##get a random color
        color = rigutils.getRandomColor()
        ##create the bone
        split_bone = net_parent.createNode('bone', 'split_' + name)
        ##Set the length of new bone to the divided amount
        split_bone.parm('length').set(split_length)
        ##set the random color
        rigutils.setDisplayColor(split_bone, color)
        ##turn of selectable
        split_bone.setSelectableInViewport(False)
        ##Turn on xray
        split_bone.useXray(True)
        ##parent the new bone to the old bone
        split_bone.setFirstInput(bone)
        ##keep the transform
        split_bone.parm('keeppos').set(True)
        ##if this is the first bone that reparent it under the root that was made for the original bone
        if num == 0:
            split_bone.setFirstInput(parent)
            ##delete the original bone
            bone.destroy()
        ##set all the transforms to be 0
        split_bone.parmTuple('t').set((0,0,0))
        ##turn on autoscope
        split_bone.parmTuple('t').setAutoscope((True, True, True))
        ##lock translates
        split_bone.parmTuple('t').lock((True, True, True))
        ##turn on autoscope for rotate
        split_bone.parmTuple('r').setAutoscope((True, True, True))
        ##place the node in a good position for node network
        split_bone.moveToGoodPosition()
        ##reset the bone variable for future iterations
        bone = split_bone
        
    return (bone)

## a function for creating FK controls
def create_FK_control(obj, size, name):
    ##get the network parent
    net_parent = obj.parent()
    
    ##names
    fk_control_name = name + '_ctrl'
    fk_auto_name = name + '_auto'
    fk_offset_name = name + '_offset'
    
    ##colors
    dull_red = hou.Color((.5,.12,.12))
    grey = hou.Color((.3,.3,.3))
    turquoise = hou.Color((0,.67,.5))
    
    name = obj.name()
    ##make offset null (1st of three nulls)
    fk_offset = net_parent.createNode('null', fk_offset_name)
    ##set flags
    fk_offset.setSelectableInViewport(False)
    fk_offset.setDisplayFlag(False)
    ##position the null in the spot of the given obj via parent
    fk_offset.setFirstInput(obj)
    ##unparent via keep position
    fk_offset.parm('keeppos').set(True)
    fk_offset.setFirstInput(None)
    ##move to nice place in network editor
    fk_offset.moveToGoodPosition()
    ##set color
    fk_offset.setColor(grey)
    
    ##create fk_auto
    fk_auto = net_parent.createNode('null', fk_auto_name)
    fk_auto.setSelectableInViewport(False)
    fk_auto.setDisplayFlag(False)
    fk_auto.setFirstInput(fk_offset)
    fk_auto.parm('keeppos').set(True)
    fk_auto.moveToGoodPosition()
    fk_auto.setColor(dull_red)
    
    ##create the fk_ctrl
    fk_ctrl = net_parent.createNode('null', fk_control_name)
    fk_ctrl.setFirstInput(fk_auto)
    fk_ctrl.moveToGoodPosition()
    fk_ctrl.parm('keeppos').set(True)
    ##change the visual to be circles
    fk_ctrl.parm('controltype').set(1)
    ##change to be the place that is perpendicular to the obj
    fk_ctrl.parm('orientation').set(3)
    ##change the size to desired size
    fk_ctrl.parm('geoscale').set(size)
    fk_ctrl.setColor(turquoise)
    
    return (fk_offset, fk_auto, fk_ctrl)


##this def is a nearly the same as rigutils.createNullAtNode except this was designed for the spine locators where the scale and rotate need to be reset
def create_null_at_node(netparent, node, name):
    ##creat null node
    null = netparent.createNode('null', name)
    ##parent it to chosen node
    null.setFirstInput(node)
    ##keep position
    null.parm('keeppos').set(True)
    ##unparent
    null.setFirstInput(None)
    ##set scale back to one
    null.parmTuple('s').set((1,1,1))
    ##set rotate back to 0
    null.parmTuple('r').set((0,0,0))
    ##clean the transforms
    null.moveParmTransformIntoPreTransform()
    
    return (null)

def create_stick_ball_null(netparent, node, name):
    turquoise = hou.Color((0,.67,.5))
    ##creat null node
    null = netparent.createNode('null', name)
    ##parent it to chosen node
    null.setFirstInput(node)
    ##keep position
    null.parm('keeppos').set(True)
    ##unparent
    null.setFirstInput(None)
    ##set scale back to one
    null.parmTuple('s').set((1,1,1))
    ##clean the transforms
    null.moveParmTransformIntoPreTransform()
    ##create new needed nodes
    control = null.node('control1/')
    ball = null.createNode('sphere')
    line = null.createNode('line')
    copy = null.createNode('copytopoints::2.0')
    merge = null.createNode('merge')
    ##parent them as needed
    copy.setInput(0, ball, 0)
    copy.setInput(1, line, 0)
    merge.setInput(0, copy, 0)
    merge.setInput(1, line, 0)
    control.setFirstInput(merge)
    ##set parms
    copy.parm('targetgroup').set('1')
    ball.parm('scale').set(.25)
    line.parm('dist').set(5)
    
    null.parm('controltype').set(7)
    null.setColor(turquoise)
    return (null)

def simple_constraint(constrained_node, ctrl_node):
    ##create the chop network in the constrained_node that will hold the constraint
    constraints = constrained_node.createNode('chopnet', 'constraints')
    ##create constraint nodes as seen in simple blend constraint
    offset = constraints.createNode('constraintoffset', 'offset')
    ctrl_obj = constraints.createNode('constraintobject', 'ctrl_node')
    world_space = constraints.createNode('constraintgetworldspace', 'getworldspace')
    simple_blend = constraints.createNode('constraintsimpleblend', 'simpleblend')
    ##set inputs
    offset.setInput(0, simple_blend, 0)
    offset.setInput(1, world_space, 0)
    simple_blend.setInput(0, world_space, 0)
    simple_blend.setInput(1, ctrl_obj, 0)
    ##set parameters
    world_space.parm('obj_path').set('../..')
    ctrl_node_path = ctrl_node.path()
    ctrl_obj.parm('obj_path').set(ctrl_node_path)
    simple_blend.parm('blend').set(1)
    ##turn on constrainability on the node
    constrained_node.parm('constraints_on').set(True)
    constrained_node.parm('constraints_path').set('constraints')
    constraints.layoutChildren()
    
    return (constraints)

def parent_constriant(constrained_node, constrainer_ctrls):
    ##create chop network in the contrained node
    constraints = constrained_node.createNode('chopnet', 'constraints')
    ##create the parent constraint node
    parent_constraint = constraints.createNode('constraintparentx', 'parent')
    ##create worldspace node
    world_space = constraints.createNode('constraintgetworldspace', 'getworldspace')
    world_space.parm('obj_path').set('../..')
    ##create parent space node
    parent_space = constraints.createNode('constraintgetparentspace', 'getparentspace')
    parent_space.parm('obj_path').set('../..')
    ##create constraint blend node
    blend = constraints.createNode('constraintblend', 'blend_parents')
    ##get the number of parents plus 1 for world space
    num_blends = len(constrainer_ctrls) + 1
    ##set the blend to have that many inputs
    blend.parm('numblends').set(num_blends)
    ##set initial parents
    parent_constraint.setInput(0, world_space, 0)
    parent_constraint.setInput(1, parent_space, 0)
    parent_constraint.setInput(2, blend, 0)
    blend.setFirstInput(parent_space)
    ##create and parent the parent ctrls
    for node in constrainer_ctrls:
        ##get the name of the node
        name = node.name()
        ##get the path of the node
        node_path = node.path()
        ##create an object constraint for that node
        parent_ctrl = constraints.createNode('constraintobjectoffset', name)
        ##parent that object constraint under the parent_space
        parent_ctrl.setFirstInput(parent_space)
        ##connect that new node to the blend 
        blend.setNextInput(parent_ctrl)
        ##set a reference to the node in the object constraint
        parent_ctrl.parm('obj_path').setExpression(node_path)
    ##layout the contraints network
    constraints.layoutChildren()
    
    return (constraints)


##this def is for creating nulls at end of bone similar to rigutils, but theirs didn't do what I wanted
def create_null_at_bone_end(bone , name):
    ##grab network parent
    netparent = bone.parent()
    ##create null
    null = netparent.createNode('null', name)
    ##place at bone.
    null.setFirstInput(bone)
    ##get the bone length expression
    bone_path = bone.path()
    bone_length = bone_path + '/length'
    bone_length_channel = '-ch("' + bone_length + '")'
    ##move down the bone
    null.parm('tz').setExpression(bone_length_channel)
    ##keep pos and unparent
    null.parm('keeppos').set(True)
    null.setFirstInput(None)
    ##delete keyframes
    null.parm('tz').deleteAllKeyframes()
    ##clean transforms
    null.moveParmTransformIntoPreTransform()
    
    return (null)

def create_face_path(netparent, cvs, name):
    ##path name
    path_name = name + '_path'
    ##create path
    path = netparent.createNode('path', path_name)
    path.useXray(True)
    ##grab the points_merge node
    points_merge = path.node('points_merge')
    ##grab delete node
    delete_ends = path.node('delete_endpoints')
    ##grab connect points node
    connect_points = path.node('connect_points')
    ##grab output_curve
    output = path.node('output_curve')
    ##create a group by range node
    extra_points = path.createNode('grouprange', 'needed_points')
    ##set to be points
    extra_points.parm('grouptype1').set(0)
    ##set to capture every 3rd point
    extra_points.parm('selecttotal1').set(3)
    ##create delete node for extra points
    delete_extra = path.createNode('delete', 'delete_extra')
    ##set group
    delete_extra.parm('group').setExpression('group1')
    ##set to delete non selected
    delete_extra.parm('negate').set(1)
    ##set to points
    delete_extra.parm('entity').set(1)
    ##set parents
    delete_extra.setFirstInput(extra_points)
    extra_points.setFirstInput(delete_ends)
    connect_points.setFirstInput(delete_extra)
    ##set to be NURBS curve
    output.parm('totype').set(4)
    ##organize
    path.layoutChildren()
    ##set up for the cvs
    num_cvs = cvs
    points_merge.parm('numobj').set(num_cvs)
    ##list for the cv_locs
    cv_locs = []
    for i in range(cvs):
        ##unique name
        cv_name = name + '_cv' + str(i)
        ##create cv
        cv = netparent.createNode('pathcv', cv_name)
        ##cv point path
        cv_path = cv.path()
        cv_point = cv_path + '/points'
        ##reference objpath parm name making sure it starts at 1
        objpath = 'objpath' + str(i + 1)
        ##set a reference to the cv point in the path
        points_merge.parm(objpath).set(cv_point)
        ##locator null name
        null_name = cv_name + '_locator'
        ##create a null to guide the cv
        cv_loc = netparent.createNode('null', null_name)
        ##parent cv to null
        cv.setFirstInput(cv_loc)
        ##set flags
        cv.setDisplayFlag(False)
        cv.setSelectableInViewport(False)
        ##make the null more resonable size and shape
        cv_loc.parm('geoscale').set(.25)
        cv_loc.parm('controltype').set(4)
        cv_loc.parm('keeppos').set(True)
        ##append the cv_loc
        cv_locs.append(cv_loc)
    
    return (cv_locs, path)


##direction: -1 or 1 depending on which way the triangle the bones make is pointing
def create_IK_FK_controls(start_bone, end_bone, parent, prefix, direction):
    ##get the parent_network from provided parent
    netparent = parent.parent()
    ##get the names
    start_bone_name = start_bone.name() + '_FK'
    ##create an FK control for each bone
    start_bone_FK = create_FK_control(start_bone,.5, start_bone_name)
    ##grab the individual nodes
    start_FK_offset = start_bone_FK[0]
    start_FK_auto = start_bone_FK[1]
    start_FK_ctrl = start_bone_FK[2]
    ##create FK constraints
    start_FK_constraint = simple_constraint(start_bone, start_FK_ctrl)
    
    ##edit the CHOP constraint to allow for switching between the constraint and world space(Which will me IK when set up)
    ##create constraint blends
    start_cblend = start_FK_constraint.createNode('constraintblend')
    ##allow for two blends (world and FK)
    start_cblend.parm('numblends').set(2)
    ##set the blend to only be rotation (the number for setting the correct blend was done through trial, other values of importance can be found in the journal)
    start_cblend.parm('writemask').set(56)
    ##set the inputs of the blends
    start_cblend.setInput(0, start_FK_constraint.node('getworldspace'), 0)
    start_cblend.setInput(1, start_FK_constraint.node('offset'), 0)
    ##set the output flag
    start_cblend.setCurrentFlag(True)
    ##set the blend to be IK (world) by default
    start_cblend.parm('blend0').set(1)
    start_cblend.parm('blend1').set(0)
    ##set up the FK parent hierachy
    start_FK_offset.setFirstInput(parent)
    
    ##create a check that if the same bone was used for both start and end, that it only makes a second FK if it doesnt match
    if end_bone != start_bone:
        end_bone_name = end_bone.name() + '_FK'
        end_bone_FK = create_FK_control(end_bone, .5, end_bone_name)
        end_FK_offset = end_bone_FK[0]
        end_FK_auto = end_bone_FK[1]
        end_FK_ctrl = end_bone_FK[2]
        end_FK_constraint = simple_constraint(end_bone, end_FK_ctrl)
        end_cblend = end_FK_constraint.createNode('constraintblend')
        end_cblend.parm('numblends').set(2)
        end_cblend.parm('writemask').set(56)
        end_cblend.setInput(0, end_FK_constraint.node('getworldspace'), 0)
        end_cblend.setInput(1, end_FK_constraint.node('offset'), 0)
        end_cblend.setCurrentFlag(True)
        end_cblend.parm('blend0').set(1)
        end_cblend.parm('blend1').set(0)
        end_FK_offset.setFirstInput(start_FK_ctrl)
    
    
    ####Create IK Twist and Goal Controls####
    ##unique names
    twist_loc_name = prefix + '_twist_loc'
    goal_loc_name = prefix + '_goal_loc'
    ##create ctrl locations for twist and goal
    ##the reason for creating nulls at end of bone is in case a single bone is fed into this for creating FK IK controls
    twist_loc = create_null_at_bone_end(start_bone, twist_loc_name)
    goal_loc = create_null_at_bone_end(end_bone, goal_loc_name)
    ##set display flags
    twist_loc.setDisplayFlag(False)
    twist_loc.setSelectableInViewport(False)
    goal_loc.setDisplayFlag(False)
    goal_loc.setSelectableInViewport(False)
    ##move the twist control away from bones based on direction
    if direction == 1:
        twist_move = .4
    else:
        twist_move = -.4
    ##move the twist control based on drirection
    twist_loc.parm('ty').set(twist_move)
    ##move the pre transforms out of pretransform for the purpose of zeroing out rotate
    twist_loc.movePreTransformIntoParmTransform()
    twist_loc.parmTuple('r').set((0,0,0))
    ##move transforms back into pre transforms
    twist_loc.moveParmTransformIntoPreTransform()
    ##unique names
    twist_name = prefix + '_twist'
    goal_name = prefix + '_goal'
    ##create 'FK' controls for these locations so we have the benefit of offset and auto
    twist_nulls = create_FK_control(twist_loc, .1, twist_name)
    goal_nulls = create_FK_control(goal_loc, .15, goal_name)
    ##grab the nodes of those sets
    twist_offset = twist_nulls[0]
    twist_auto = twist_nulls[1]
    twist_ctrl = twist_nulls[2]
    gaol_offset = goal_nulls[0]
    goal_auto = goal_nulls[1]
    goal_ctrl = goal_nulls[2]
    ##set the ctrls to look a bit differant than my default FK ctrl
    ##box
    twist_ctrl.parm('controltype').set(2)
    ##box and null
    goal_ctrl.parm('controltype').set(5)
    ##set parents
    twist_loc.setFirstInput(twist_ctrl)
    goal_loc.setFirstInput(goal_ctrl)
    
    ####CREATE KINEMATICS####
    ##search for chop net and if it doesn't exist make one
    chop_list = []
    for node in netparent.children():
        if node.type().name() == 'chopnet':
            chop_list.append(node)
    ##check if any nodes where added to the list, if yes than that is out kin_net
    if chop_list == []:
        kin_net = netparent.createNode('chopnet', 'KIN_Chops')
    else:
        kin_net = chop_list[0]
    ##inverskin unique name
    kin_name = 'KIN_' + prefix
    ##create kinematics node
    kin_node = kin_net.createNode('inversekin', kin_name)
    ##set to parms to be inverse kin with twist
    kin_node.parm('solvertype').set(2)
    ##get paths to all our nodes that will make the kinematics
    twist_path = twist_loc.path()
    goal_path = goal_loc.path()
    start_bone_path = start_bone.path()
    end_bone_path = end_bone.path()
    ##pump in all our paths into the solver
    kin_node.parm('bonerootpath').set(start_bone_path)
    kin_node.parm('boneendpath').set(end_bone_path)
    kin_node.parm('endaffectorpath').set(goal_path)
    kin_node.parm('twistaffectorpath').set(twist_path)
    ##default set blend to 1
    kin_node.parm('blend').set(1)
    ##kin path
    kin_path = kin_node.path()
    ##set the solver into the bones that need it
    start_bone.parm('solver').set(kin_path)
    if end_bone != start_bone:
        end_bone.parm('solver').set(kin_path)
    
    ##set some parameter chanels so that when the kin solver is turned off/on the blends do the same
    ##get the kin_node blend parameter path for referencing
    kin_blend_channel = 'ch("' + kin_path + '/blend")'
    ##set the blend nodes in each bone
    start_cblend.parm('blend0').setExpression(kin_blend_channel)
    start_cblend.parm('blend1').setExpression('1 - ' + kin_blend_channel)
    if end_bone != start_bone:
        end_cblend.parm('blend0').setExpression(kin_blend_channel)
        end_cblend.parm('blend1').setExpression('1 - ' + kin_blend_channel)
        
        return(start_FK_ctrl, end_FK_ctrl, twist_ctrl, goal_ctrl, kin_node)
    
    return(start_FK_ctrl, twist_ctrl, goal_ctrl, kin_node)

def makeBonesFromCurve(curve, chainname, numberofbones, kintype, stretch):
    ##get the netparent
    network = hou.node(curve.parent().path())
    ##get the path of the curve
    curve_path = hou.node(curve.path())
    ##get the displayed node of the path subnet
    curve_display = curve.displayNode()
    ##make sure the chainname is a string
    chainname = str(chainname)
    ##get the curve length
    curve_geo_len = curve_display.geometry().prims()[0].intrinsicValue("measuredperimeter")
    ##create a list for appending nodes to that we can then use the list later to delete uneeded nodes
    nodes = []
    # make a root null
    chain_root = network.createNode("null", chainname + "_root")
    chain_root.moveToGoodPosition()
    
    chop_node = []
    # make Follow Curve IK if kintype is 1, if 0 than no kinematics
    if kintype is 1:
        ##check if a chop node already exsists
        for node in network.children():
            if node.type().name() == 'chopnet':
                chop_node.append(node)
                ##print chop_node
        if chop_node == []:
            curveIK = network.createNode("chopnet", 'KIN_Chops')
            
        else:
            curveIK = chop_node[0]
        curveIK.moveToGoodPosition()
        ##create an inverse kin and set it to follow curve
        chainFollowIK = curveIK.createNode("inversekin", chainname + "bone_IK")
        chainFollowIK.parm("solvertype").set(4)
        curveIK.moveToGoodPosition()
    ##determine the parent 
    parent = chain_root
    
    # make resample node and make the number of segmants equal to number of bones
    resample = curve_path.createNode("resample", "slideframe_resample")
    nodes.append(resample)
    ##turn off segmant length
    resample.parm("dolength").set(0)
    ##turn on segment count
    resample.parm("dosegs").set(1)
    ##set segments to be number of bones
    resample.parm("segs").set(numberofbones)
    ##parent the resample to curve display node
    resample.setFirstInput(curve_display)
    resample.moveToGoodPosition()
    
    # make slideframe
    slideframe = curve_path.createNode("attribwrangle", "slideframe")
    nodes.append(slideframe)
    slideframe.parm("class").set(0)
    slideframesnippet = slideframe.parm("snippet")
    slideframestr = """
int n = npoints(0);

addpointattrib(geoself(), "tan", {0, 0, 0});
addpointattrib(geoself(), "nml", {0, 0, 0});
addpointattrib(geoself(), "binml", {0, 0, 0});

vector nml[];
vector tan[];

resize(nml, n);
resize(tan, n);


tan[0] = normalize(point(0, "P", 1) - point(0, "P", 0));
nml[0] = set(0,1,0);
if (normalize(nml[0]) == normalize(tan[0])){
    nml[0] = set(0,0,1);
    }

nml[0] = cross(nml[0], tan[0]);

for (int i = 1; i < n; i++)
{
    vector p0 = point(0, "P", i - 1);
    vector p1 = point(0, "P", i);
    vector t;
    
    if (i < n - 1)
        t = normalize(point(0, "P", i + 1) - p1);
    else
        t = normalize(p1 - p0);
        
    tan[i] = t;
    nml[i] = slideframe(p0, tan[i - 1], nml[i - 1], p1, t);   
}

for (int i = 0; i < n; i++)
{
    setpointattrib(geoself(), "nml", i, nml[i]);
    setpointattrib(geoself(), "tan", i, -1*tan[i]);
    setpointattrib(geoself(), "binml", i, -1*cross(tan[i], nml[i]));
}
    """
    
    slideframesnippet.set(slideframestr)    
    slideframe.setFirstInput(resample)
    slideframe.moveToGoodPosition()
    curve_geo = slideframe.geometry()
    
    bones = []
    ##creating bones
    for b in range(int(numberofbones)):
        ##create bone
        bone = network.createNode("bone", chainname + "bone" + str(b +1))
        ##move to a good position in network editor
        bone.moveToGoodPosition()
        ##get a random color and assign it to the bone
        color = rigutils.getRandomColor()
        rigutils.setDisplayColor(bone, color)
        
        ##if this is the first bone and the kinematics are on, then put this bones path as root bone
        if b is 0 and kintype is 1:
            chainFollowIK.parm("bonerootpath").set(bone.path())
        
        ##get the b (iteration number) point of the resample curve
        cur_pt = curve_geo.iterPoints()[b]
        ##get the b+1 (iteration number + 1) point of the resample curve
        cur_pt1 = curve_geo.iterPoints()[b+1]
        ##get the position of the curent point
        cur_pt_loc = cur_pt.attribValue("P")
        ##place the bone at the b point
        bone.parmTuple("t").set(cur_pt_loc)
        ##set the bone length by doing messurement math between b and b+1
        blength = hou.Vector3(cur_pt1.attribValue("P")) - hou.Vector3(cur_pt.attribValue("P"))
        bone_length = blength.length()
        bone.parm("length").set(bone_length)

        ##use attributes set up in the wrangle to orient the bone correctly
        tan = cur_pt.attribValue("tan")
        nml = cur_pt.attribValue("nml")
        binml = cur_pt.attribValue("binml")
        rot = hou.Matrix3([nml, binml, tan]).extractRotates('zyx')
        rot_null = hou.Matrix3([nml, binml, tan]).extractRotates('xyz')
        bone.parmTuple("r").set(rot)
        ##clean transforms
        bone.moveParmTransformIntoPreTransform()
        ##if this is the first bone parent it to the root
        if b is 0:
            chain_root.parmTuple("t").set(cur_pt_loc)
            chain_root.parmTuple("r").set(rot_null)
            chain_root.parm("geoscale").set(bone_length/5)
            chain_root.parm("controltype").set(1)
            chain_root.parm("shadedmode").set(1)
        ##parent the created bone to the parent, which if 0 will be root, and after that will be the most recent bone
        bone.parm("keeppos").set(True)
        bone.setFirstInput(parent)
        bone.parmTuple("R").set((0, 0, 0))
        parent = bone
        bones.append(bone)
        
    # layout children
    for bone in bones:
        ##turn on xray
        bone.useXray(True)
        
        hou.hscript("bonealigncapture -c {}".format(bone.path()))
        ##set some new capture parameters based on how big the bones are
        capturetop = bone.evalParmTuple('ccrtopcap')
        len = bone.evalParm('length')
        newval = len * capturetop[0]
        bone.parmTuple('ccrtopcap').set((newval, newval, newval))
        bone.parmTuple('ccrbotcap').set((newval, newval, newval))
        bone.parmTuple("crtopcap").set((newval, newval, newval))
        bone.parmTuple("crbotcap").set((newval, newval, newval)) 
        bone.moveToGoodPosition()
        ##set up stretch if desired
        if stretch == 1:
            path_name = curve.name()
            arc_expression = 'arclen("../' + path_name + '", 1, 0, 1)/' + str(numberofbones)
            ##print arc_expression
            bone.parm('length').setExpression(arc_expression)
    ##finish setting up the IK settup
    if kintype is 1:
        chainFollowIK.parm("boneendpath").set(parent.path())
        chainFollowIK.parm("curvepath").set(curve.path())
        for bone in bones:
            bone.parm("solver").set(chainFollowIK.path())
    
    for node in nodes:
        node.destroy()
        
    ##kepp position if parented
    chain_root.parm('keeppos').set(True)
    ##grab the first cv to parent the root to
    ##get the points merge of the path that holds reference paths to the cvs
    points_merge = curve.node('points_merge')
    ##get the firct cv reference
    points_path = points_merge.parm('objpath1').eval()
    ##replace the poitns with nothing so we only have a path to the cv obj node
    cv0_path = points_path.replace('points','')
    ##make that path into a node
    cv0 = hou.node(cv0_path)
    ##parent the root
    chain_root.setFirstInput(cv0)
        
    return (bones)
    
def get_script_dir():
    script_file = os.path.abspath(__file__)
    #print script_path
    return os.path.dirname(script_file)


class RigCreatorUI(QtWidgets.QDialog):
    
    def __init__(self):
        ##Rin the initialization on the inherited QDialog class
        super(RigCreatorUI, self).__init__()
        
        ##set the window title
        self.setWindowTitle('Rig Creator')
        
        #Assemble the file path for the ui file
        ui_file_path = os.path.join(get_script_dir(), 'rig_creator_ui.ui')
        #replace any os path seperators with forwardslashes for houdini to laod ui
        ui_file_path = ui_file_path.replace(os.path.sep, '/')
        ##print (ui_file_path)
        
        #create a Qfile object from the file path
        qfile_object = QtCore.QFile(ui_file_path)
        #open the QFile object
        qfile_object.open(QtCore.QFile.ReadOnly)
        
        #create a QUI loader
        loader = QtUiTools.QUiLoader()
        #load the file and save it to a property
        self.ui = loader.load(qfile_object, parentWidget = self)
        """
        above two line can be written as:
        self.ui = QtUiTools.QUiLoader().load(qfile_object, parentWidget=self)
        """
        ######BUTTON CALLS#########
        ##button call for browsing files to import
        self.ui.btnImportBrowse.clicked.connect(self.import_browse)
        
        ##button call for browsing files to save to 
        self.ui.btnHDABrowse.clicked.connect(self.save_browse)
        
        ##button call for importing the model
        self.ui.btnImport.clicked.connect(self.create_mesh)
        
        ##button call for placing locators
        self.ui.btnCreateLocators.clicked.connect(self.create_locators)
        
        ##button call for create bones
        self.ui.btnCreateBones.clicked.connect(self.create_bones)
        
        ##button call for capturing skin wieghts
        self.ui.btnCaptureMesh.clicked.connect(self.capture_mesh)
        
        
        ##close the file handle
        qfile_object.close()
        
        ##set window parent to houdini main window
        self.setParent(hou.qt.mainWindow(), QtCore.Qt.Window)
        
        ##show the UI
        self.show()
        
    ##def to close the window and unparent it from the main qt Window
    def closeEvent(self, event):
        self.setParent(None)
        
    ## defs needed for button calls and UI elements
    def import_browse(self):
        ##grab the script directory, we are going to use this as the starting point of our browse
        default_folder = get_script_dir()
        ##make sure that the directory has forward slashes and not backslashes
        default_folder = default_folder.replace(os.path.sep, '/')
        ##debug print
        ##print (default_folder)
        ##create a variable that calls a houdini browse function
        result = hou.ui.selectFile(default_folder, 'Choose your Model')
        ##if nothing was selected, do nothing
        if result is None:
            return
        ##update the text feild next to the browse button with the selected file's path
        self.ui.lineImportModel.setText(result)
        
    def save_browse(self):
        ##grab the script directory, we are going to use this as the starting point of our browse
        default_folder = get_script_dir()
        ##make sure that the directory has forward slashes and not backslashes
        default_folder = default_folder.replace(os.path.sep, '/')
        ##debug print
        ##print (default_folder)
        ##create a variable that calls a houdini browse function
        result = hou.ui.selectFile(default_folder, 'Choose HDA save directory', False, hou.fileType.Directory)
        ##if nothing was selected, do nothing
        if result is None:
            return
        ##update the text feild next to the browse button with the selected file's path
        self.ui.lineHDASave.setText(result)
    
    def create_mesh(self):
        if self.ui.lineImportModel.text() == '':
            hou.ui.displayMessage('Character Geometry Not Chosen', ('OK',), hou.severityType.Warning)
            return
        ##create a varaible storing the file path from the browse function
        geo_file = self.ui.lineImportModel.text()
        geo_file = geo_file.replace(os.path.sep, '/')
        ##debug print
        ##print (geo_file)
        ##create a variable holding the rig name that was chosen
        rig_name = self.ui.lineRigName.text()
        ##if the name feild is empty, than use the default name
        if rig_name == '':
            rig_name = 'character_rig'
        ##debug print
        ##print (rig_name)
        ##grab the object level
        obj_level = hou.node('/obj')
        
        ##grab the custom save location for the HDA if it exists
        hda_save_loc = self.ui.lineHDASave.text()
        ##if the user din't choose a location, just save to where the script is
        if hda_save_loc == '':
            hda_save_loc = get_script_dir()
        
        ##create a custom HDA name based off the chosen rig name
        hda_name = rig_name + '.hda'
        
        ##create a complete file directory to where the HDA will be saved using the hda_name and hda_save_loc
        hda_file_name = os.path.join(hda_save_loc, hda_name)
        hda_file_name = hda_file_name.replace(os.path.sep, '/')
        
        ##create a subnetwork node and save it to a varible for later use
        rig_net = obj_level.createNode('subnet', rig_name)
        #create the digital asset from the subnet
        rig_net = rig_net.createDigitalAsset(rig_name, hda_file_name, None, 0, 1)
        ##grab the true Hda definition
        hda_def = rig_net.type().definition()
        
        ####set the HDA's default parameter folders to be hidden####
        ##Make a copy of the parmTempalteGroup
        parm_temp_group = rig_net.parmTemplateGroup()
        ##fine the transform folder
        trans_folder = parm_temp_group.findFolder('Transform')
        ##set it to hidden
        parm_temp_group.hide(trans_folder, True)
        ##find the subnet folder
        subnet_folder = parm_temp_group.findFolder('Subnet')
        ##set it to hidden
        parm_temp_group.hide(subnet_folder, True)
        ##reset the template group to the HDA
        rig_net.setParmTemplateGroup(parm_temp_group)
        
        ####create a geo node in the new HDA for referenceing the geo chosen by user####
        #create a unique name for the geo node
        geo_ref_name = rig_name + '_geo'
        #create the node
        geo_ref = rig_net.createNode('geo', geo_ref_name)
        #create a file node in the geo node holding the user chosen geometry
        file_ref_name = rig_name + '_ref'
        file_ref = geo_ref.createNode('file', file_ref_name)
        ##set the geometry file to reference the chosen geo
        file_ref.parm('file').set(geo_file)
        ##inject the user selected geo into the HDA itself
        ##grab the name of the geo node earlier created
        node_name = geo_ref.name()
        ##create a name based on the geo node name that will be a Houdini geometry
        geometry_name = node_name + '.bgeo'
        ##grab the folder data
        geometry = file_ref.geometry().data()
        ##add the geometry to the hda
        hda_def.addSection(geometry_name, geometry) 
        ##set the file node to the new geometry in HDA
        file_ref.parm('file').set('opdef:../..?'+geometry_name)
        
        ##check if it is being imported from maya and scale it down if it is
        if self.ui.chkFromMaya.isChecked() == True:
            ##create a transform to scale down the geo
            scale_down = geo_ref.createNode('xform', 'maya_scale_down')
            ##parent the node to the file ref
            scale_down.setFirstInput(file_ref)
            ##set the scale to be 1/100
            scale_down.parm('scale').set(.01)
            ##set render and display flag
            scale_down.setRenderFlag(True)
            scale_down.setDisplayFlag(True)
            ##layout the nodes in the geo network
            geo_ref.layoutChildren()
        
        
        ##create starting null objects
        hidden_trans = rig_net.createNode('null', 'hidden_transform')
        master = rig_net.createNode('null', 'master')
        
        #parent the hidden transform under the subnet's indirect input by accessing it's indirect input and choosing first of the list
        hidden_trans.setFirstInput(rig_net.indirectInputs()[0])
        
        ##set visibility and selectability and inputs
        geo_ref.setSelectableInViewport(False)
        hidden_trans.setDisplayFlag(False)
        hidden_trans.setSelectableInViewport(False)
        master.setDisplayFlag(False)
        master.setSelectableInViewport(False)
        master.setFirstInput(hidden_trans)
        ####change master's shape####
        ##set the control display to be circles
        master.parm('controltype').set(1)
        ##set the control to only be on ZX plane
        master.parm('orientation').set(2)
        ##make the control slightly larger
        master.parm('geoscale').set(1.75)
        
        ##comment and color nodes
        geo_ref.setComment('This node holds the Character Geo reference')
        hidden_trans.setComment('This node is for any Layout Work when the charater needs to be moved without affecting the animation')
        ##set a color rgb value
        purple = hou.Color((.27,.185,.6))
        grey = hou.Color((.3,.3,.3))
        turquoise = hou.Color((0,.67,.5))
        ##set the node color 
        geo_ref.setColor(purple)
        hidden_trans.setColor(grey)
        master.setColor(turquoise)
        
        ##layout nodes in the rig net so far
        rig_net.layoutChildren()
        
        ##Enable the group box holding the AutoRig Functions and disable import functions
        self.ui.grpAutoRig.setEnabled(True)
        self.ui.grpImport.setEnabled(False)
    
    ##def for creating all null nodes that will be used as locators for creating bones
    def create_locators(self):
        ####grab a reference back to the rig subnet network####
        ##grab the rig name
        rig_name = self.ui.lineRigName.text()
        ##create a full directory to that node
        hda_node = '/obj/' + rig_name
        ##select that node
        rig_net = hou.node(hda_node)
        
        ##create an empty lists for appending nodes to for creating for loops later
        locator_list = []
        L_side_list = []
        foot_list = []
        finger_list = []
        face_list = []
        
        ##create a COG locator
        COG = rig_net.createNode('null', 'spine_base_locator')
        COG.setParms({'ty':.95, 'tz':.015})
        COG.parm('controltype').set(6)
        locator_list.append(COG)
        
        ##create spine_top locator
        ##call def for creating a null node that has a line to another node
        spine_top = create_null_pointer(rig_net, COG, 'spine_top_locator')
        ##place that node in a space that makes sence
        spine_top.setParms({'ty':1.445, 'tz':-.006})
        ##keep position when parenting
        spine_top.parm('keeppos').set(1)
        ##parent to previous node
        spine_top.setFirstInput(COG)
        ##apend node to any list that it relates to for later
        locator_list.append(spine_top)
        
        ##create mid neck locator
        mid_neck = create_null_pointer(rig_net, spine_top, 'mid_neck_locator')
        mid_neck.setParms({'ty':1.5, 'tz':.012})
        mid_neck.parm('keeppos').set(1)
        mid_neck.setFirstInput(spine_top)
        locator_list.append(mid_neck)
        face_list.append(mid_neck)
        
        ##create skull base
        skull_base = create_null_pointer(rig_net, mid_neck, 'skull_base_locator')
        skull_base.setParms({'ty':1.568, 'tz':.015})
        skull_base.parm('keeppos').set(1)
        skull_base.setFirstInput(mid_neck)
        locator_list.append(skull_base)
        face_list.append(skull_base)
        
        ##create head top
        head_top = create_null_pointer(rig_net, skull_base, 'head_top_locator')
        head_top.setParms({'ty': 1.725, 'tz':.015})
        head_top.parm('keeppos').set(1)
        head_top.setFirstInput(skull_base)
        locator_list.append(head_top)
        face_list.append(head_top)
        
        ##create jaw hindge
        jaw_hindge = create_null_pointer(rig_net, skull_base, 'jaw_hindge_locator')
        jaw_hindge.setParms({'ty':1.587, 'tz':.055})
        jaw_hindge.parm('keeppos').set(1)
        jaw_hindge.setFirstInput(skull_base)
        locator_list.append(jaw_hindge)
        face_list.append(jaw_hindge)
        
        ##create chin locator
        chin = create_null_pointer(rig_net, jaw_hindge, 'chin_locator')
        chin.setParms({'ty':1.521, 'tz':.136})
        chin.parm('keeppos').set(1)
        chin.setFirstInput(jaw_hindge)
        locator_list.append(chin)
        face_list.append(chin)
        
        ##create tailbone locator
        tailbone = create_null_pointer(rig_net, COG, 'tailbone_locator')
        tailbone.setParms({'ty':.89, 'tz':-.03})
        tailbone.parm('keeppos').set(1)
        tailbone.setFirstInput(COG)
        locator_list.append(tailbone)
        
        ##create left hip
        L_hip = create_null_pointer(rig_net, COG, 'L_hip_locator')
        L_hip.setParms({'tx':.094,'ty':.893,'tz':.018})
        L_hip.parm('keeppos').set(1)
        L_hip.setFirstInput(COG)
        locator_list.append(L_hip)
        L_side_list.append(L_hip)
        
        ##create left knee
        L_knee = create_null_pointer(rig_net, L_hip, 'L_knee_locator')
        L_knee.setParms({'tx':.15,'ty':.5,'tz':.039})
        L_knee.parm('keeppos').set(1)
        L_knee.setFirstInput(L_hip)
        locator_list.append(L_knee)
        L_side_list.append(L_knee)
        
        ##create L ankle 
        L_ankle = create_null_pointer(rig_net, L_knee, 'L_ankle_locator')
        L_ankle.setParms({'tx':.203,'ty':.087,'tz':.012})
        L_ankle.parm('keeppos').set(1)
        L_ankle.setFirstInput(L_knee)
        locator_list.append(L_ankle)
        L_side_list.append(L_ankle)
        
        ##create L ball
        L_ball = create_null_pointer(rig_net, L_ankle, 'L_ball_locator')
        L_ball.setParms({'tx':.203,'ty':.015,'tz':.137})
        L_ball.parm('keeppos').set(1)
        L_ball.setFirstInput(L_ankle)
        locator_list.append(L_ball)
        L_side_list.append(L_ball)
        foot_list.append(L_ball)
        
        ##create L toe tip
        L_toe_tip = create_null_pointer(rig_net, L_ball, 'L_toe_tip_locator')
        L_toe_tip.setParms({'tx':.203, 'ty':.015, 'tz':.214})
        L_toe_tip.parm('keeppos').set(1)
        L_toe_tip.setFirstInput(L_ball)
        locator_list.append(L_toe_tip)
        L_side_list.append(L_toe_tip)
        foot_list.append(L_toe_tip)
        
        ##create L heel
        L_heel = create_null_pointer(rig_net, L_ankle, 'L_heel_locator')
        L_heel.setParms({'tx':.2, 'tz':-0.033})
        L_heel.parm('keeppos').set(1)
        L_heel.setFirstInput(L_ankle)
        locator_list.append(L_heel)
        L_side_list.append(L_heel)
        foot_list.append(L_heel)
        
        ##create L_foot_inner
        L_foot_inner = create_null_pointer(rig_net, L_ball, 'L_foot_inner_locator')
        L_foot_inner.setParms({'tx':.16,'tz':.136})
        L_foot_inner.parm('keeppos').set(1)
        L_foot_inner.setFirstInput(L_ball)
        locator_list.append(L_foot_inner)
        L_side_list.append(L_foot_inner)
        foot_list.append(L_foot_inner)
        
        ##create L_foot_outer
        L_foot_outer = create_null_pointer(rig_net, L_ball, 'L_foot_outer_locator')
        L_foot_outer.setParms({'tx':.253, 'tz':.136})
        L_foot_outer.parm('keeppos').set(1)
        L_foot_outer.setFirstInput(L_ball)
        locator_list.append(L_foot_outer)
        L_side_list.append(L_foot_outer)
        foot_list.append(L_foot_outer)
        
        ##create L_shoulder
        L_shoulder = create_null_pointer(rig_net, spine_top, 'L_shoulder_locator')
        L_shoulder.setParms({'tx':.17,'ty':1.4,'tz':-.005})
        L_shoulder.parm('keeppos').set(1)
        L_shoulder.setFirstInput(spine_top)
        locator_list.append(L_shoulder)
        L_side_list.append(L_shoulder)
        
        ##create L_elbow
        L_elbow = create_null_pointer(rig_net, L_shoulder, 'L_elbow_locator')
        L_elbow.setParms({'tx':.369,'ty':1.18,'tz':-.01})
        L_elbow.parm('keeppos').set(1)
        L_elbow.setFirstInput(L_shoulder)
        locator_list.append(L_elbow)
        L_side_list.append(L_elbow)
        
        ##create L_ wrist
        L_wrist = create_null_pointer(rig_net, L_elbow, 'L_wrist_locator')
        L_wrist.setParms({'tx':.545,'ty':1.003,'tz':.078})
        L_wrist.parm('keeppos').set(1)
        L_wrist.setFirstInput(L_elbow)
        locator_list.append(L_wrist)
        L_side_list.append(L_wrist)
        
        ##create thumb_base
        thumb_base = create_null_pointer(rig_net, L_wrist, 'L_thumb_base_locator')
        thumb_base.setParms({'tx':.543,'ty':.985,'tz':.12})
        thumb_base.parm('keeppos').set(1)
        thumb_base.setFirstInput(L_wrist)
        locator_list.append(thumb_base)
        L_side_list.append(thumb_base)
        finger_list.append(thumb_base)
        
        ##create thumb_mid
        thumb_mid = create_null_pointer(rig_net, thumb_base, 'L_thumb_mid_locator')
        thumb_mid.setParms({'tx':.544,'ty':.973,'tz':.14})
        thumb_mid.parm('keeppos').set(1)
        thumb_mid.setFirstInput(thumb_base)
        locator_list.append(thumb_mid)
        L_side_list.append(thumb_mid)
        finger_list.append(thumb_mid)
        
        ##create thumb_end
        thumb_end = create_null_pointer(rig_net, thumb_mid, 'L_thumb_end_locator')
        thumb_end.setParms({'tx':.545,'ty':.946,'tz':.168})
        thumb_end.parm('keeppos').set(1)
        thumb_end.setFirstInput(thumb_mid)
        locator_list.append(thumb_end)
        L_side_list.append(thumb_end)
        finger_list.append(thumb_end)
        
        ##create thumb_tip_point
        thumb_tip_point = create_null_pointer(rig_net, thumb_end, 'L_thumb_tip_point_locator')
        thumb_tip_point.setParms({'tx':.5455,'ty':.923,'tz':.187})
        thumb_tip_point.parm('keeppos').set(1)
        thumb_tip_point.setFirstInput(thumb_end)
        locator_list.append(thumb_tip_point)
        L_side_list.append(thumb_tip_point)
        finger_list.append(thumb_tip_point)
        
        ##create index_base
        index_base = create_null_pointer(rig_net, L_wrist, 'L_index_base_locator')
        index_base.setParms({'tx':.599,'ty':.9377,'tz':.145})
        index_base.parm('keeppos').set(1)
        index_base.setFirstInput(L_wrist)
        locator_list.append(index_base)
        L_side_list.append(index_base)
        finger_list.append(index_base)
        
        ##create index_mid
        index_mid = create_null_pointer(rig_net, index_base, 'L_index_mid_locator')
        index_mid.setParms({'tx':.611,'ty':.9164,'tz':.159})
        index_mid.parm('keeppos').set(1)
        index_mid.setFirstInput(index_base)
        locator_list.append(index_mid)
        L_side_list.append(index_mid)
        finger_list.append(index_mid)
        
        ##create index_end
        index_end = create_null_pointer(rig_net, index_mid, 'L_index_end_locator')
        index_end.setParms({'tx':.617,'ty':.8937,'tz':.171})
        index_end.parm('keeppos').set(1)
        index_end.setFirstInput(index_mid)
        locator_list.append(index_end)
        L_side_list.append(index_end)
        finger_list.append(index_end)
        
        ##create index_tip_point
        index_tip_point = create_null_pointer(rig_net, index_end, 'L_index_tip_point_locator')
        index_tip_point.setParms({'tx':.62,'ty':.8682,'tz':.183})
        index_tip_point.parm('keeppos').set(1)
        index_tip_point.setFirstInput(index_end)
        locator_list.append(index_tip_point)
        L_side_list.append(index_tip_point)
        finger_list.append(index_tip_point)
        
        ##create middle_base
        middle_base = create_null_pointer(rig_net, L_wrist, 'L_middle_base_locator')
        middle_base.setParms({'tx':.6061,'ty':.9320,'tz':.1181})
        middle_base.parm('keeppos').set(1)
        middle_base.setFirstInput(L_wrist)
        locator_list.append(middle_base)
        L_side_list.append(middle_base)
        finger_list.append(middle_base)
        
        ##create middle_mid
        middle_mid = create_null_pointer(rig_net, middle_base, 'L_middle_mid_locator')
        middle_mid.setParms({'tx':.623,'ty':.9006,'tz':.129})
        middle_mid.parm('keeppos').set(1)
        middle_mid.setFirstInput(middle_base)
        locator_list.append(middle_mid)
        L_side_list.append(middle_mid)
        finger_list.append(middle_mid)
        
        ##create middle_end
        middle_end = create_null_pointer(rig_net, middle_mid, 'L_middle_end_locator')
        middle_end.setParms({'tx':.632,'ty':.8729,'tz':.137})
        middle_end.parm('keeppos').set(1)
        middle_end.setFirstInput(middle_mid)
        locator_list.append(middle_end)
        L_side_list.append(middle_end)
        finger_list.append(middle_end)
        
        ##create middle_tip_point
        middle_tip_point = create_null_pointer(rig_net, middle_end, 'L_middle_tip_point_locator')
        middle_tip_point.setParms({'tx':.636,'ty':.8465,'tz':.144})
        middle_tip_point.parm('keeppos').set(1)
        middle_tip_point.setFirstInput(middle_end)
        locator_list.append(middle_tip_point)
        L_side_list.append(middle_tip_point)
        finger_list.append(middle_tip_point)
        
        ##create ring_base
        ring_base = create_null_pointer(rig_net, L_wrist, 'L_ring_base_locator')
        ring_base.setParms({'tx':.608,'ty':.9270,'tz':.0958})
        ring_base.parm('keeppos').set(1)
        ring_base.setFirstInput(L_wrist)
        locator_list.append(ring_base)
        L_side_list.append(ring_base)
        finger_list.append(ring_base)
        
        ##create ring_mid
        ring_mid = create_null_pointer(rig_net, ring_base, 'L_ring_mid_locator')
        ring_mid.setParms({'tx':.623,'ty':.9018,'tz':.099})
        ring_mid.parm('keeppos').set(1)
        ring_mid.setFirstInput(ring_base)
        locator_list.append(ring_mid)
        L_side_list.append(ring_mid)
        finger_list.append(ring_mid)
        
        ##create ring_end
        ring_end = create_null_pointer(rig_net, ring_mid, 'L_ring_end_locator')
        ring_end.setParms({'tx':.632,'ty':.8764,'tz':.102})
        ring_end.parm('keeppos').set(1)
        ring_end.setFirstInput(ring_mid)
        locator_list.append(ring_end)
        L_side_list.append(ring_end)
        finger_list.append(ring_end)
        
        ##create ring_tip_point
        ring_tip_point = create_null_pointer(rig_net, ring_end, 'L_ring_tip_point_locator')
        ring_tip_point.setParms({'tx':.638,'ty':.8485,'tz':.105})
        ring_tip_point.parm('keeppos').set(1)
        ring_tip_point.setFirstInput(ring_end)
        locator_list.append(ring_tip_point)
        L_side_list.append(ring_tip_point)
        finger_list.append(ring_tip_point)
        
        ##create pinky_base
        pinky_base = create_null_pointer(rig_net, L_wrist, 'L_pinky_base_locator')
        pinky_base.setParms({'tx':.602,'ty':.9297,'tz':.072})
        pinky_base.parm('keeppos').set(1)
        pinky_base.setFirstInput(L_wrist)
        locator_list.append(pinky_base)
        L_side_list.append(pinky_base)
        finger_list.append(pinky_base)
        
        ##create pinky_mid
        pinky_mid = create_null_pointer(rig_net, pinky_base, 'L_pinky_mid_locator')
        pinky_mid.setParms({'tx':.611,'ty':.9065,'tz':.072})
        pinky_mid.parm('keeppos').set(1)
        pinky_mid.setFirstInput(pinky_base)
        locator_list.append(pinky_mid)
        L_side_list.append(pinky_mid)
        finger_list.append(pinky_mid)
        
        ##create pinky_end
        pinky_end = create_null_pointer(rig_net, pinky_mid, 'L_pinky_end_locator')
        pinky_end.setParms({'tx':.616,'ty':.8895,'tz':.072})
        pinky_end.parm('keeppos').set(1)
        pinky_end.setFirstInput(pinky_mid)
        locator_list.append(pinky_end)
        L_side_list.append(pinky_end)
        finger_list.append(pinky_end)
        
        ##create pinky_tip_point
        pinky_tip_point = create_null_pointer(rig_net, pinky_end, 'L_pinky_tip_point_locator')
        pinky_tip_point.setParms({'tx':.618,'ty':.8679,'tz':.072})
        pinky_tip_point.parm('keeppos').set(1)
        pinky_tip_point.setFirstInput(pinky_end)
        locator_list.append(pinky_tip_point)
        L_side_list.append(pinky_tip_point)
        finger_list.append(pinky_tip_point)
        
        ####FACE CURVES AND LOCATORS####
        ##left cheek
        cheek = create_face_path(rig_net, 3, 'L_cheek')
        ##extract nodes
        cheek_locs = cheek[0]
        cheek_loc0 = cheek_locs[0]
        cheek_loc0.parmTuple('t').set((.065, 1.586, 0.061))
        cheek_loc1 = cheek_locs[1]
        cheek_loc1.parmTuple('t').set((.053, 1.58, 0.103))
        cheek_loc2 = cheek_locs[2]
        cheek_loc2.parmTuple('t').set((.043, 1.538, 0.103))
        face_list.append(cheek_loc0)
        face_list.append(cheek_loc1)
        face_list.append(cheek_loc2)
        
        ##left brow
        brow = create_face_path(rig_net, 3, 'L_brow')
        ##extract nodes and place in a default space that makes sence
        brow_locs = brow[0]
        brow_loc0 = brow_locs[0]
        brow_loc0.parmTuple('t').set((.007, 1.63, .137))
        brow_loc1 = brow_locs[1]
        brow_loc1.parmTuple('t').set((.034, 1.643, .137))
        brow_loc2 = brow_locs[2]
        brow_loc2.parmTuple('t').set((.053, 1.626, .115))
        face_list.append(brow_loc0)
        face_list.append(brow_loc1)
        face_list.append(brow_loc2)
        
        ##left squint
        squint = create_face_path(rig_net, 3, 'L_squint')
        squint_locs = squint[0]
        squint_loc0 = squint_locs[0]
        squint_loc0.parmTuple('t').set((.016, 1.607, .127))
        squint_loc1 = squint_locs[1]
        squint_loc1.parmTuple('t').set((.038, 1.6, .127))
        squint_loc2 = squint_locs[2]
        squint_loc2.parmTuple('t').set((.052, 1.608, .114))
        face_list.append(squint_loc0)
        face_list.append(squint_loc1)
        face_list.append(squint_loc2)
        
        ##left smile_line
        smile_line = create_face_path(rig_net, 3, 'L_smile_line')
        smile_locs = smile_line[0]
        smile_loc0 = smile_locs[0]
        smile_loc0.parmTuple('t').set((.016, 1.6, .13))
        smile_loc1 = smile_locs[1]
        smile_loc1.parmTuple('t').set((.033, 1.58, .128))
        smile_loc2 = smile_locs[2]
        smile_loc2.parmTuple('t').set((.034, 1.557, .124))
        face_list.append(smile_loc0)
        face_list.append(smile_loc1)
        face_list.append(smile_loc2)
        
        ##left nostril
        nostril = create_face_path(rig_net, 3, 'L_nostril')
        nostril_locs = nostril[0]
        nostril_loc0 = nostril_locs[0]
        nostril_loc0.parmTuple('t').set((.014, 1.593, .135))
        nostril_loc1 = nostril_locs[1]
        nostril_loc1.parmTuple('t').set((.022, 1.584, .128))
        nostril_loc2 = nostril_locs[2]
        nostril_loc2.parmTuple('t').set((.015, 1.578, .135))
        face_list.append(nostril_loc0)
        face_list.append(nostril_loc1)
        face_list.append(nostril_loc2)
        
        ##upper lip locs
        upper_lip = create_face_path(rig_net, 5, 'upper_lip')
        u_lip_locs = upper_lip[0]
        u_lip_loc0 = u_lip_locs[0]
        u_lip_loc0.parmTuple('t').set((-.024, 1.557, .131))
        u_lip_loc1 = u_lip_locs[1]
        u_lip_loc1.parmTuple('t').set((-.014, 1.561, .143))
        u_lip_loc2 = u_lip_locs[2]
        u_lip_loc2.parmTuple('t').set((0, 1.561, .146))
        u_lip_loc3 = u_lip_locs[3]
        u_lip_loc3.parmTuple('t').set((.014, 1.562, .143))
        u_lip_loc4 = u_lip_locs[4]
        u_lip_loc4.parmTuple('t').set((.024, 1.557, .131))
        face_list.append(u_lip_loc0)
        face_list.append(u_lip_loc1)
        face_list.append(u_lip_loc2)
        face_list.append(u_lip_loc3)
        face_list.append(u_lip_loc4)
        u_lip_path = upper_lip[1]
        
        ##lower lip locs
        lower_lip = create_face_path(rig_net, 5, 'lower_lip')
        l_lip_locs = lower_lip[0]
        l_lip_loc0 = l_lip_locs[0]
        l_lip_loc0.parmTuple('t').set((-.023, 1.555, .13))
        l_lip_loc1 = l_lip_locs[1]
        l_lip_loc1.parmTuple('t').set((-.014, 1.554, .14))
        l_lip_loc2 = l_lip_locs[2]
        l_lip_loc2.parmTuple('t').set((0, 1.552, .143))
        l_lip_loc3 = l_lip_locs[3]
        l_lip_loc3.parmTuple('t').set((.014, 1.554, .14))
        l_lip_loc4 = l_lip_locs[4]
        l_lip_loc4.parmTuple('t').set((.023, 1.555, .13))
        face_list.append(l_lip_loc0)
        face_list.append(l_lip_loc1)
        face_list.append(l_lip_loc2)
        face_list.append(l_lip_loc3)
        face_list.append(l_lip_loc4)
        l_lip_path = upper_lip[1]
        
        
        ##layout all the new nodes
        rig_net.layoutChildren()
        ##create a network box to place all the locators
        locators_box = rig_net.createNetworkBox('locator_nulls')
        
        ##create some colors for coloring nodes
        cyan = hou.Color((0,.7,.7))
        dark_cyan = hou.Color((0,.4,.4))
        ##for every node in the locator_list change its network color and its display scale and add it to the box
        for node in locator_list:
            node.setColor(cyan)
            node.parm('geoscale').set(.2)
            locators_box.addItem(node)
        ##minimize the box and color it
        locators_box.setMinimized(True)
        locators_box.setColor(dark_cyan)
        ##for all null nodes that relate to the foot change the display scale
        for node in foot_list:
            node.parm('geoscale').set(.1)
        ##for all null nodes that relate to the hand change the display scale
        for node in finger_list:
            node.parm('geoscale').set(.03)
        for node in face_list:
            node.parm('geoscale').set(.02)
        ##re-layout everything
        rig_net.layoutChildren()
        
    def create_bones(self):
        
        ##grab all the references back to the different levels of the node network
        ##top level
        obj_level = hou.node('/obj')
        ##grab the rig name
        rig_name = self.ui.lineRigName.text()
        #reset rig name to be a full path
        rig_name = rig_name + '/'
        ##get the rig network
        rig_net = obj_level.node(rig_name)
        ##grab the master null node
        master = rig_net.node('master/')
        
        ##for every null node in the rig_net (locators) turn off its display and selectability
        for each in rig_net.children():
            ##debug print
            ##print (each.type().name())
            if each.type().name() == 'null':
                each.setDisplayFlag(False)
                each.setSelectableInViewport(False)
        
        ##create a list of the spine locators
        spine_nodes = []
        spine_nodes.append(rig_net.node('spine_base_locator/'))
        spine_nodes.append(rig_net.node('spine_top_locator/'))
        
        ##create a bone for the spine and split it 6 times
        spine_bone = create_root_bone_chain(master, spine_nodes, 'spine')
        spine_root = spine_bone[0]
        spine_bone = spine_bone[1]
        ##get the spine root from the created bones from earlier
        spine_split = split_bone(spine_bone, 6)
        
        ##create a null in the middle of the last spine bone for creation of a shoulder bone
        wing_locator = rig_net.createNode('null', 'wing_locator')
        ##place that locator in the middle of the last spine bone by
        ##parent to last spine bone
        wing_locator.setFirstInput(rig_net.node('split_spine_bone6/'))
        ##moving the locator halfway up the bone length
        wing_locator.parm('tz').setExpression('-ch("../split_spine_bone6/length")/2')
        ##uparenting it
        wing_locator.parm('keeppos').set(True)
        wing_locator.setFirstInput(None)
        ##move the locator away fromt he center axis
        wing_locator.parm('tx').set(.05)
        ##set flags
        wing_locator.setSelectableInViewport(False)
        wing_locator.setDisplayFlag(False)
        ##grab the locator box
        locator_nulls = rig_net.findNetworkBox('locator_nulls')
        locator_nulls.addItem(wing_locator)
        
        ##shoulder list
        shoulder_list =  []
        shoulder_list.append(wing_locator)
        shoulder_list.append(rig_net.node('L_shoulder_locator'))
        
        ##create a list for the arm locators
        arm_locators = []
        arm_locators.append(rig_net.node('L_shoulder_locator'))
        arm_locators.append(rig_net.node('L_elbow_locator'))
        arm_locators.append(rig_net.node('L_wrist_locator'))
        
        ##hand
        hand_locators = []
        hand_locators.append(rig_net.node('L_wrist_locator'))
        hand_locators.append(rig_net.node('L_middle_base_locator'))
        
        ##create a list for the finger locators
        ##thumb
        thumb_locators = []
        thumb_locators.append(rig_net.node('L_thumb_base_locator'))
        thumb_locators.append(rig_net.node('L_thumb_mid_locator'))
        thumb_locators.append(rig_net.node('L_thumb_end_locator'))
        thumb_locators.append(rig_net.node('L_thumb_tip_point_locator'))
        ##index
        index_locators = []
        index_locators.append(rig_net.node('L_index_base_locator'))
        index_locators.append(rig_net.node('L_index_mid_locator'))
        index_locators.append(rig_net.node('L_index_end_locator'))
        index_locators.append(rig_net.node('L_index_tip_point_locator'))
        ##middle
        middle_locators = []
        middle_locators.append(rig_net.node('L_middle_base_locator'))
        middle_locators.append(rig_net.node('L_middle_mid_locator'))
        middle_locators.append(rig_net.node('L_middle_end_locator'))
        middle_locators.append(rig_net.node('L_middle_tip_point_locator'))
        ##ring
        ring_locators = []
        ring_locators.append(rig_net.node('L_ring_base_locator'))
        ring_locators.append(rig_net.node('L_ring_mid_locator'))
        ring_locators.append(rig_net.node('L_ring_end_locator'))
        ring_locators.append(rig_net.node('L_ring_tip_point_locator'))
        ##pinky
        pinky_locators = []
        pinky_locators.append(rig_net.node('L_pinky_base_locator'))
        pinky_locators.append(rig_net.node('L_pinky_mid_locator'))
        pinky_locators.append(rig_net.node('L_pinky_end_locator'))
        pinky_locators.append(rig_net.node('L_pinky_tip_point_locator'))
        
        ##create a list for the leg locators
        leg_locators = []
        leg_locators.append(rig_net.node('L_hip_locator'))
        leg_locators.append(rig_net.node('L_knee_locator'))
        leg_locators.append(rig_net.node('L_ankle_locator'))
        
        foot_locators = []
        foot_locators.append(rig_net.node('L_ankle_locator'))
        foot_locators.append(rig_net.node('L_ball_locator'))
        foot_locators.append(rig_net.node('L_toe_tip_locator'))
        
        ##tailbone list
        tailbone_locators = []
        tailbone_locators.append(rig_net.node('spine_base_locator'))
        tailbone_locators.append(rig_net.node('tailbone_locator'))
        
        ##neck list
        neck_locators = []
        neck_locators.append(rig_net.node('spine_top_locator'))
        neck_locators.append(rig_net.node('mid_neck_locator'))
        neck_locators.append(rig_net.node('skull_base_locator'))
        
        ##head list
        head_locators = []
        head_locators.append(rig_net.node('skull_base_locator'))
        head_locators.append(rig_net.node('head_top_locator'))
        
        ##jaw locators
        jaw_locators = []
        jaw_locators.append(rig_net.node('jaw_hindge_locator'))
        jaw_locators.append(rig_net.node('chin_locator'))
        
        ####creating the bones####
        ##create pelvis root and bones
        pelvis = create_root_bone_chain(spine_root, tailbone_locators, 'pelvis')
        ##grab the pelvis bone
        pelvis_bone = pelvis[1]
        ##create neck root and bones
        neck_bones = create_root_bone_chain(spine_split, neck_locators, 'neck')
        ##grab the neck last bone
        neck_last = neck_bones[2]
        head_bone = create_root_bone_chain(neck_last, head_locators, 'head')
        head_last = head_bone[1]
        jaw_bone = create_root_bone_chain(head_last, jaw_locators, 'jaw')
        jaw_last = jaw_bone[1]
        shoulder_bone = create_root_bone_chain(spine_split, shoulder_list, 'L_shoulder')
        shoulder_last = shoulder_bone[1]
        ##Rotating the hand and shoulder bone to be a good position for my default model that I am basing this tool off of and will ship the tool with        
        shoulder_last.parm('rz').set(-170)
        arm_bones = create_root_bone_chain(shoulder_last, arm_locators, 'L_arm')
        arm_last = arm_bones[2]
        hand_bone = create_root_bone_chain(arm_last, hand_locators, 'L_hand')
        hand_last = hand_bone[1]
        ##Rotating the hand and shoulder bone to be a good position for my default model that I am basing this tool off of and will ship the tool with
        hand_last.parm('rz').set(-20)
        leg_bones = create_root_bone_chain(pelvis_bone, leg_locators, 'L_leg')
        leg_last = leg_bones[2]
        foot_bones = create_root_bone_chain(leg_last, foot_locators, 'L_foot')
        foot_last = foot_bones[2]
        thumb_bones = create_root_bone_chain(hand_last, thumb_locators, 'L_thumb')
        index_bones = create_root_bone_chain(hand_last, index_locators, 'L_index')
        middle_bones = create_root_bone_chain(hand_last, middle_locators, 'L_middle')
        ring_bones = create_root_bone_chain(hand_last, ring_locators, 'L_ring')
        pinky_bones = create_root_bone_chain(hand_last, pinky_locators, 'L_pinky')
        
        ####FACE BONES####
        L_cheek_path = rig_net.node('L_cheek_path')
        makeBonesFromCurve(L_cheek_path, 'L_cheek', 6, 1, 1)
        brow_path = rig_net.node('L_brow_path')
        makeBonesFromCurve(brow_path, 'L_brow', 6, 1, 1)
        squint_path = rig_net.node('L_squint_path')
        makeBonesFromCurve(squint_path, 'L_squint', 3, 1, 1)
        smile_line_path = rig_net.node('L_smile_line_path')
        makeBonesFromCurve(smile_line_path, 'L_smile_line', 4, 1, 1)
        nostril_path = rig_net.node('L_nostril_path')
        makeBonesFromCurve(nostril_path, 'L_nostril', 3, 1, 1)
        lower_lip_path = rig_net.node('lower_lip_path')
        makeBonesFromCurve(lower_lip_path, 'lower_lip', 6, 1, 1)
        upper_lip_path = rig_net.node('upper_lip_path')
        makeBonesFromCurve(upper_lip_path, 'upper_lip', 6, 1, 1)
        
        ##turn keep position on in case user wants to reorient bones
        for bone in rig_net.children():
            if bone.type().name() == 'bone':
                bone.parm('keeppos').set(True)
                
        rig_net.layoutChildren()
        
    def capture_mesh(self):
        ##grab all the references back to the different levels of the node network
        ##top level
        obj_level = hou.node('/obj')
        ##grab the rig name
        rig_name = self.ui.lineRigName.text()
        #reset rig name to be a full path
        rig_name = rig_name + '/'
        ##get the rig network
        rig_net = obj_level.node(rig_name)
        ##grab the master null node
        master = rig_net.node('master/')
        
        ##colors
        purple = hou.Color((.27,.185,.6))
        dull_red = hou.Color((.5,.12,.12))
        grey = hou.Color((.3,.3,.3))
        turquoise = hou.Color((0,.67,.5))
        
        ##create a list for all the bones
        bones_list = []
        
        ##gather all the bones into a list
        for each in rig_net.children():
            if each.type().name() == 'bone':
                bones_list.append(each)
                each.setSelectableInViewport(False)
                ##"zero" out the rotation and position of the bones
                each.moveParmTransformIntoPreTransform()
                ##set all rest angles to 0
                each.parmTuple('R').set((0,0,0))
            ##turn off all null display including root nulls
            if each.type().name() == 'null':
                each.setDisplayFlag(False)
                each.setSelectableInViewport(False)
        
        ##create a list for ctrls
        ctrl_list = []
        
        ####MASTER CONTROL####
        ##turn master control back on
        master.setDisplayFlag(True)
        master.setSelectableInViewport(True)
        ##add master to control list
        ctrl_list.append(master)
        
        ####MASTER UI ELEMENTS####
        ##create the master folder for the HDA
        ##grab the hda parmTemplateGroup
        rig_ptg = rig_net.parmTemplateGroup()
        ##create master folder
        master_folder = hou.FolderParmTemplate('master_folder', 'Master')
        
        ##create the needed folders in master folder
        m_display_folder = hou.FolderParmTemplate('m_display_folder', 'Display')
        m_action_folder = hou.FolderParmTemplate('m_action_folder', 'Actions')
        m_ctrl_folder = hou.FolderParmTemplate('m_ctrl_folder', 'Controls')
        ##change to simple
        m_display_folder.setFolderType(hou.folderType.Simple)
        m_action_folder.setFolderType(hou.folderType.Simple)
        m_ctrl_folder.setFolderType(hou.folderType.Simple)
        
        ##create the needed menu parameters to the display folder
        ##create a menu item with name 'm_display' label 'Master Display', Menu items of 0 and 1, with names for those items as OFF and ON and set it to be ON by default
        m_display = hou.MenuParmTemplate('m_display', 'Master Display', ['0', '1'], ['OFF', 'ON'], 1)
        m_geo_display = hou.MenuParmTemplate('m_geo_display', 'Geo Display', ['0', '1'], ['OFF', 'ON'], 1)
        m_bone_display = hou.MenuParmTemplate('m_bone_display', 'Bone Display', ['0', '1'], ['OFF', 'ON'], 0)
        m_ctrl_dispaly = hou.MenuParmTemplate('m_ctrl_display', 'Controls Display', ['0', '1'], ['OFF', 'ON'], 1)
        ##add the menu items to the folder
        m_display_folder.addParmTemplate(m_display)
        m_display_folder.addParmTemplate(m_geo_display)
        m_display_folder.addParmTemplate(m_bone_display)
        m_display_folder.addParmTemplate(m_ctrl_dispaly)
        ##add the m_display folder to the master folder
        master_folder.addParmTemplate(m_display_folder)
        
        ##create buttons for the actions folder
        all_default = hou.ButtonParmTemplate('set_all_to_default', 'Set ALL to Default')
        all_key = hou.ButtonParmTemplate('set_all_keys', 'Set ALL Keys')
        m_action_sep = hou.SeparatorParmTemplate('m_action_sep')
        master_default = hou.ButtonParmTemplate('set_master_to_default', 'Set Master to Default')
        master_key = hou.ButtonParmTemplate('set_master_key', 'Set Master Key')
        ##add the buttons to the actions folder
        m_action_folder.addParmTemplate(all_default)
        m_action_folder.addParmTemplate(all_key)
        m_action_folder.addParmTemplate(m_action_sep)
        m_action_folder.addParmTemplate(master_default)
        m_action_folder.addParmTemplate(master_key)
        ##add the action folder to the master folder
        master_folder.addParmTemplate(m_action_folder)
        
        ##create floats for the master control
        m_trans = hou.FloatParmTemplate('master_trans', 'Master Translate', 3)
        m_rot = hou.FloatParmTemplate('master_rot', 'Master Rotate', 3)
        m_scale = hou.FloatParmTemplate('master_scale', 'Master Scale', 1, [1])
        ##add the floats to the control folder
        m_ctrl_folder.addParmTemplate(m_trans)
        m_ctrl_folder.addParmTemplate(m_rot)
        m_ctrl_folder.addParmTemplate(m_scale)
        ##add the ctrl folder to master
        master_folder.addParmTemplate(m_ctrl_folder)
        
        ##add the master folder to the template group
        rig_ptg.addParmTemplate(master_folder)
        ##reset the rig_net template back to the copy we have been editing
        rig_net.setParmTemplateGroup(rig_ptg)
        
        ####MASTER UI TO CONTROL IMPLEMENTATION####
        ##set parameters to reference the HDA created parameters as if "promoting"
        master.parm('tx').setExpression('ch("../master_transx")')
        master.parm('ty').setExpression('ch("../master_transy")')
        master.parm('tz').setExpression('ch("../master_transz")')
        master.parm('rx').setExpression('ch("../master_rotx")')
        master.parm('ry').setExpression('ch("../master_roty")')
        master.parm('rz').setExpression('ch("../master_rotz")')
        master.parm('scale').setExpression('ch("../master_scale")')
        ##display
        master.parm('tdisplay').set(True)
        master.parm('display').setExpression('ch("../m_display")')
        
        
        ####CREATE COG CTRL####
        spine_1 = rig_net.node('split_spine_bone1/')
        COG = create_null_at_node(rig_net, spine_1, 'COG_ctrl')
        COG.parm('ty').setExpression('ch("../split_spine_bone1/length")/2')
        COG.parm('ty').deleteAllKeyframes()
        COG.moveParmTransformIntoPreTransform()
        COG.setFirstInput(master)
        COG.setColor(turquoise)
        COG.parm('controltype').set(1)
        COG.parm('orientation').set(2)
        COG.parmTuple('dcolor').set((1,0,1))
        ctrl_list.append(COG)
        
        
        ####SPINE CURVE####
        ##create the spine curve for FK and IK functions
        spine_path = rig_net.createNode('path', 'spine_path')
        ##find the points merge node in the path node
        points_merge = spine_path.node('points_merge/')
        ##allow for three objects to link to the path
        points_merge.parm('numobj').set(3)
        ##find the rest of the needed nodes in the path network
        delete_endpoints = spine_path.node('delete_endpoints/')
        connect_points = spine_path.node('connect_points/')
        output_curve = spine_path.node('output_curve/')
        ##create the path cv points
        spine_base_cv = rig_net.createNode('pathcv', 'spine_base_cv')
        spine_mid_cv = rig_net.createNode('pathcv', 'spine_mid_cv')
        spine_top_cv = rig_net.createNode('pathcv', 'spine_top_cv')
        ##shink the z axis on the cvs for a smoother path creation
        spine_base_cv.parm('sz').set(.1)
        spine_mid_cv.parm('sz').set(.1)
        spine_top_cv.parm('sz').set(.1)
        ##get the path to the cv's points node
        spine_base_cv_path = spine_base_cv.path() + '/points'
        spine_mid_cv_path = spine_mid_cv.path() + '/points'
        spine_top_cv_path = spine_top_cv.path() + '/points'
        ##input the cvs into the points merge
        points_merge.parm('objpath1').set(spine_base_cv_path)
        points_merge.parm('objpath2').set(spine_mid_cv_path)
        points_merge.parm('objpath3').set(spine_top_cv_path)
        ##delete the mid_cv's extension points in preperation of changing to a NURBS 
        delete_mid = spine_path.createNode('delete', 'delete_midpoints')
        delete_mid.setFirstInput(delete_endpoints)
        connect_points.setFirstInput(delete_mid)
        spine_path.layoutChildren()
        ##set parms on the delete node for getting rid of those mid cvs
        delete_mid.parm('entity').set(1)
        delete_mid.parm('group').set('2 4')
        ##turn the curve to a NURBS
        output_curve.parm('totype').set(4)
        ####position the cvs in the correct spots####
        ##spine base
        spine_base_cv.setFirstInput(rig_net.node('split_spine_bone1'))
        spine_base_cv.parm('keeppos').set(True)
        spine_base_cv.setFirstInput(None)
        ##spine mid
        spine_mid_cv.setFirstInput(rig_net.node('split_spine_bone4'))
        spine_mid_cv.parm('keeppos').set(True)
        spine_mid_cv.setFirstInput(None)
        ##spine top
        spine_top_cv.setFirstInput(rig_net.node('split_spine_bone6'))
        spine_top_cv.parm('tz').setExpression('-ch("../split_spine_bone6/length")')
        spine_top_cv.parm('keeppos').set(True)
        spine_top_cv.setFirstInput(None)
        spine_top_cv.parm('tz').deleteAllKeyframes()
        ##set flags
        spine_base_cv.setSelectableInViewport(False)
        spine_base_cv.setDisplayFlag(False)
        spine_mid_cv.setSelectableInViewport(False)
        spine_mid_cv.setDisplayFlag(False)
        spine_top_cv.setSelectableInViewport(False)
        spine_top_cv.setDisplayFlag(False)
        spine_path.setSelectableInViewport(False)
        spine_path.setDisplayFlag(False)
        
        ####Spine Controls####
        ##create the IK controls
        hip_IK = create_null_at_node(rig_net, spine_base_cv, 'hip_IK_ctrl')
        mid_IK = create_null_at_node(rig_net, spine_mid_cv, 'mid_IK_ctrl')
        chest_IK = create_null_at_node(rig_net, spine_top_cv, 'chest_IK_ctrl')
        ##set some parameters so the ctrls look nicer
        ##control type to box
        hip_IK.parm('controltype').set(2)
        mid_IK.parm('controltype').set(2)
        chest_IK.parm('controltype').set(2)
        ##change display scale (not actual scale)
        hip_IK.setParms({'geosizex':.7, 'geosizey':.1, 'geosizez':.6})
        mid_IK.setParms({'geosizex':.6, 'geosizey':.025, 'geosizez':.5})
        chest_IK.setParms({'geosizex':.7, 'geosizey':.1, 'geosizez':.4})
        ##move the center of the mid IK forward a bit to compensate for spine curve
        mid_IK.parm('geocenterz').set(.03)
        ##changing the node color
        hip_IK.setColor(turquoise)
        mid_IK.setColor(turquoise)
        chest_IK.setColor(turquoise)
        ##create the FK controls
        FK_A = create_null_at_node(rig_net, rig_net.node('split_spine_bone1'), 'spine_A_FK_ctrl')
        FK_B = create_null_at_node(rig_net, rig_net.node('split_spine_bone3'), 'spine_B_FK_ctrl')
        FK_C = create_null_at_node(rig_net, rig_net.node('split_spine_bone5'), 'spine_C_FK_ctrl')
        ##set parms for the looks
        ##cotnrol type to be circle in ZX plaen
        FK_A.parm('controltype').set(1)
        FK_B.parm('controltype').set(1)
        FK_C.parm('controltype').set(1)
        FK_A.parm('orientation').set(2)
        FK_B.parm('orientation').set(2)
        FK_C.parm('orientation').set(2)
        ##change display and center to be nice looking by default
        FK_A.parmTuple('geosize').set((.8,.8,.6))
        FK_B.parmTuple('geosize').set((.8,.8,.6))
        FK_B.parm('geocenterz').set(.02)
        FK_C.parmTuple('geosize').set((.8,.8,.6))
        FK_C.parm('geocenterz').set(.03)
        ##changing the controls color
        FK_A.parmTuple('dcolor').set((0,1,.5))
        FK_B.parmTuple('dcolor').set((0,1,.5))
        FK_C.parmTuple('dcolor').set((0,1,.5))
        ##change the node color
        FK_A.setColor(turquoise)
        FK_B.setColor(turquoise)
        FK_C.setColor(turquoise)
        ##set inputs
        FK_A.setFirstInput(COG)
        FK_B.setFirstInput(FK_A)
        FK_C.setFirstInput(FK_B)
        hip_IK.setFirstInput(FK_A)
        mid_IK.setFirstInput(FK_B)
        chest_IK.setFirstInput(FK_C)
        spine_base_cv.setFirstInput(hip_IK)
        spine_mid_cv.setFirstInput(mid_IK)
        spine_top_cv.setFirstInput(chest_IK)
        spine_root = rig_net.node('spine_root')
        spine_path.setFirstInput(spine_root)
        spine_root.setFirstInput(hip_IK)
        ##append controls to list
        ctrl_list.append(FK_A)
        ctrl_list.append(FK_B)
        ctrl_list.append(FK_C)
        ctrl_list.append(chest_IK)
        ctrl_list.append(mid_IK)
        ctrl_list.append(hip_IK)
        
        ####Spine Kinematics####
        chop_node = []
        #check if a chop node already exsists
        for node in rig_net.children():
            if node.type().name() == 'chopnet':
                chop_node.append(node)
                ##print chop_node
        if chop_node == []:
            kin_net = rig_net.createNode("chopnet", 'KIN_Chops')
        else:
            kin_net = chop_node[0]
        ##create a kinematics solver
        spine_kin = kin_net.createNode('inversekin', 'KIN_spine')
        ##change the solver type to follow curve
        spine_kin.parm('solvertype').set(4)
        ##set the root and end bones
        spine_kin.parm('bonerootpath').set('../../split_spine_bone1')
        spine_kin.parm('boneendpath').set('../../split_spine_bone6')
        ##set the curve
        spine_kin.parm('curvepath').set('../../spine_path')
        ##set spine bones to follow the spine kinematics
        rig_net.node('split_spine_bone1').parm('solver').set('../KIN_Chops/KIN_spine/')
        rig_net.node('split_spine_bone2').parm('solver').set('../KIN_Chops/KIN_spine/')
        rig_net.node('split_spine_bone3').parm('solver').set('../KIN_Chops/KIN_spine/')
        rig_net.node('split_spine_bone4').parm('solver').set('../KIN_Chops/KIN_spine/')
        rig_net.node('split_spine_bone5').parm('solver').set('../KIN_Chops/KIN_spine/')
        rig_net.node('split_spine_bone6').parm('solver').set('../KIN_Chops/KIN_spine/')
        ##set spine to be able to stretch with curve
        rig_net.node('split_spine_bone1').parm('length').setExpression('arclen("../spine_path", 0, 0, 1)/6')
        rig_net.node('split_spine_bone2').parm('length').setExpression('arclen("../spine_path", 0, 0, 1)/6')
        rig_net.node('split_spine_bone3').parm('length').setExpression('arclen("../spine_path", 0, 0, 1)/6')
        rig_net.node('split_spine_bone4').parm('length').setExpression('arclen("../spine_path", 0, 0, 1)/6')
        rig_net.node('split_spine_bone5').parm('length').setExpression('arclen("../spine_path", 0, 0, 1)/6')
        rig_net.node('split_spine_bone6').parm('length').setExpression('arclen("../spine_path", 0, 0, 1)/6')
        
        ####PELVIS CONTROL####
        pelvis_root = rig_net.node('pelvis_root')
        pelvis_ctrl = create_stick_ball_null(rig_net, pelvis_root, 'pelvis_ctrl')
        pelvis_ctrl.parm('rx').set(-85)
        pelvis_ctrl.parm('geoscale').set(.04)
        pelvis_ctrl.parmTuple('dcolor').set((.5,.25,0))
        pelvis_ctrl.setColor(turquoise)
        pelvis_root.setFirstInput(pelvis_ctrl)
        pelvis_ctrl.setFirstInput(hip_IK)
        pelvis_ctrl.moveParmTransformIntoPreTransform()
        ctrl_list.append(pelvis_ctrl)
        
        ####SPINE UI####
        ##grab the hda parmTemplateGroup
        rig_ptg = rig_net.parmTemplateGroup()
        ##create spine folder
        spine_folder = hou.FolderParmTemplate('spine_folder', 'Spine')
        
        ##create the needed folders in master folder
        s_display_folder = hou.FolderParmTemplate('s_display_folder', 'Display')
        s_action_folder = hou.FolderParmTemplate('s_action_folder', 'Actions')
        s_ctrl_folder = hou.FolderParmTemplate('s_ctrl_folder', 'Controls')
        ##change to simple
        s_display_folder.setFolderType(hou.folderType.Simple)
        s_action_folder.setFolderType(hou.folderType.Simple)
        s_ctrl_folder.setFolderType(hou.folderType.Simple)
        
        ##create the needed menu parameters to the display folder
        s_bone_display = hou.MenuParmTemplate('s_bone_display', 'Bone Display', ['0', '1'], ['OFF', 'ON'], 0)
        s_ctrl_dispaly = hou.MenuParmTemplate('s_ctrl_display', 'Controls Display', ['0', '1'], ['OFF', 'ON'], 1)
        ##add to the folder
        s_display_folder.addParmTemplate(s_bone_display)
        s_display_folder.addParmTemplate(s_ctrl_dispaly)
        ##add folder to spine_folder
        spine_folder.addParmTemplate(s_display_folder)
        
        ##create buttons for the actions folder
        spine_default = hou.ButtonParmTemplate('set_spine_to_default', 'Set Spine to Default')
        spine_key = hou.ButtonParmTemplate('set_spine_key', 'Set Spine Keys')
        ##add the buttons to the actions folder
        s_action_folder.addParmTemplate(spine_default)
        s_action_folder.addParmTemplate(spine_key)
        ##add the action folder to the master folder
        spine_folder.addParmTemplate(s_action_folder)
        
        ##create floats for the master control
        COG_trans = hou.FloatParmTemplate('COG_trans', 'COG Translate', 3)
        COG_rot = hou.FloatParmTemplate('COG_rot', 'COG Rotate', 3)
        FK_C_rot = hou.FloatParmTemplate('FK_C_rot', 'FK C Rotate', 3)
        FK_B_rot = hou.FloatParmTemplate('FK_B_rot', 'FK B Rotate', 3)
        FK_A_rot = hou.FloatParmTemplate('FK_A_rot', 'FK A Rotate', 3)
        chest_IK_trans = hou.FloatParmTemplate('chest_IK_trans', 'Chest IK Translate', 3)
        chest_IK_rot = hou.FloatParmTemplate('chest_IK_rot', 'Chest IK Rotate', 3)
        mid_IK_trans = hou.FloatParmTemplate('mid_IK_trans', 'Mid IK Translate', 3)
        hip_IK_trans = hou.FloatParmTemplate('hip_IK_trans', 'Hip IK Translate', 3)
        hip_IK_rot = hou.FloatParmTemplate('hip_IK_rot', 'Hip IK Rotate', 3)
        pelvis_rot = hou.FloatParmTemplate('pelvis_rot', 'Pelvis Rotate', 3)
        ##add the floats to the control folder
        s_ctrl_folder.addParmTemplate(COG_trans)
        s_ctrl_folder.addParmTemplate(COG_rot)
        s_ctrl_folder.addParmTemplate(FK_C_rot)
        s_ctrl_folder.addParmTemplate(FK_B_rot)
        s_ctrl_folder.addParmTemplate(FK_A_rot)
        s_ctrl_folder.addParmTemplate(chest_IK_trans)
        s_ctrl_folder.addParmTemplate(chest_IK_rot)
        s_ctrl_folder.addParmTemplate(mid_IK_trans)
        s_ctrl_folder.addParmTemplate(hip_IK_trans)
        s_ctrl_folder.addParmTemplate(hip_IK_rot)
        s_ctrl_folder.addParmTemplate(pelvis_rot)
        ##add the ctrl folder to master
        spine_folder.addParmTemplate(s_ctrl_folder)
        
        ##add the spine folder to the template group
        rig_ptg.addParmTemplate(spine_folder)
        ##reset the rig_net template back to the copy we have been editing
        rig_net.setParmTemplateGroup(rig_ptg)
        
        ##make sure that all the ctrls have clean transforms before creating references
        for ctrl in ctrl_list:
            ctrl.moveParmTransformIntoPreTransform()
        
        ####SPINE UI CONTROL IMPLEMENTATION####
        COG.parm('tx').setExpression('ch("../COG_transx")')
        COG.parm('ty').setExpression('ch("../COG_transy")')
        COG.parm('tz').setExpression('ch("../COG_transz")')
        COG.parm('rx').setExpression('ch("../COG_rotx")')
        COG.parm('ry').setExpression('ch("../COG_roty")')
        COG.parm('rz').setExpression('ch("../COG_rotz")')
        FK_A.parm('rx').setExpression('ch("../FK_A_rotx")')
        FK_A.parm('ry').setExpression('ch("../FK_A_roty")')
        FK_A.parm('rz').setExpression('ch("../FK_A_rotz")')
        FK_B.parm('rx').setExpression('ch("../FK_B_rotx")')
        FK_B.parm('ry').setExpression('ch("../FK_B_roty")')
        FK_B.parm('rz').setExpression('ch("../FK_B_rotz")')
        FK_C.parm('rx').setExpression('ch("../FK_C_rotx")')
        FK_C.parm('ry').setExpression('ch("../FK_C_roty")')
        FK_C.parm('rz').setExpression('ch("../FK_C_rotz")')
        chest_IK.parm('tx').setExpression('ch("../chest_IK_transx")')
        chest_IK.parm('ty').setExpression('ch("../chest_IK_transy")')
        chest_IK.parm('tz').setExpression('ch("../chest_IK_transz")')
        chest_IK.parm('rx').setExpression('ch("../chest_IK_rotx")')
        chest_IK.parm('ry').setExpression('ch("../chest_IK_roty")')
        chest_IK.parm('rz').setExpression('ch("../chest_IK_rotz")')
        mid_IK.parm('tx').setExpression('ch("../mid_IK_transx")')
        mid_IK.parm('ty').setExpression('ch("../mid_IK_transy")')
        mid_IK.parm('tz').setExpression('ch("../mid_IK_transz")')
        hip_IK.parm('tx').setExpression('ch("../hip_IK_transx")')
        hip_IK.parm('ty').setExpression('ch("../hip_IK_transy")')
        hip_IK.parm('tz').setExpression('ch("../hip_IK_transz")')
        hip_IK.parm('rx').setExpression('ch("../hip_IK_rotx")')
        hip_IK.parm('ry').setExpression('ch("../hip_IK_roty")')
        hip_IK.parm('rz').setExpression('ch("../hip_IK_rotz")')
        pelvis_ctrl.parm('rx').setExpression('ch("../pelvis_rotx")')
        pelvis_ctrl.parm('ry').setExpression('ch("../pelvis_roty")')
        pelvis_ctrl.parm('rz').setExpression('ch("../pelvis_rotz")')
        ##displayability options implementation
        ##bones
        ##if master bone display and spine bone display are on than set value 1, else 0
        rig_net.node('split_spine_bone1').parm('tdisplay').set(True)
        rig_net.node('split_spine_bone2').parm('tdisplay').set(True)
        rig_net.node('split_spine_bone3').parm('tdisplay').set(True)
        rig_net.node('split_spine_bone4').parm('tdisplay').set(True)
        rig_net.node('split_spine_bone5').parm('tdisplay').set(True)
        rig_net.node('split_spine_bone6').parm('tdisplay').set(True)
        rig_net.node('pelvis_bone1').parm('tdisplay').set(True)
        rig_net.node('split_spine_bone1').parm('display').setExpression('if (ch("../s_bone_display") == 1 && ch("../m_bone_display") == 1, 1, 0)')
        rig_net.node('split_spine_bone2').parm('display').setExpression('if (ch("../s_bone_display") == 1 && ch("../m_bone_display") == 1, 1, 0)')
        rig_net.node('split_spine_bone3').parm('display').setExpression('if (ch("../s_bone_display") == 1 && ch("../m_bone_display") == 1, 1, 0)')
        rig_net.node('split_spine_bone4').parm('display').setExpression('if (ch("../s_bone_display") == 1 && ch("../m_bone_display") == 1, 1, 0)')
        rig_net.node('split_spine_bone5').parm('display').setExpression('if (ch("../s_bone_display") == 1 && ch("../m_bone_display") == 1, 1, 0)')
        rig_net.node('split_spine_bone6').parm('display').setExpression('if (ch("../s_bone_display") == 1 && ch("../m_bone_display") == 1, 1, 0)')
        rig_net.node('pelvis_bone1').parm('display').setExpression('if (ch("../s_bone_display") == 1 && ch("../m_bone_display") == 1, 1, 0)')
        ##ctrls
        COG.parm('tdisplay').set(True)
        FK_A.parm('tdisplay').set(True)
        FK_B.parm('tdisplay').set(True)
        FK_C.parm('tdisplay').set(True)
        hip_IK.parm('tdisplay').set(True)
        mid_IK.parm('tdisplay').set(True)
        chest_IK.parm('tdisplay').set(True)
        pelvis_ctrl.parm('tdisplay').set(True)
        COG.parm('display').setExpression('if (ch("../s_ctrl_display") == 1 && ch("../m_ctrl_display") == 1, 1, 0)')
        FK_A.parm('display').setExpression('if (ch("../s_ctrl_display") == 1 && ch("../m_ctrl_display") == 1, 1, 0)')
        FK_B.parm('display').setExpression('if (ch("../s_ctrl_display") == 1 && ch("../m_ctrl_display") == 1, 1, 0)')
        FK_C.parm('display').setExpression('if (ch("../s_ctrl_display") == 1 && ch("../m_ctrl_display") == 1, 1, 0)')
        hip_IK.parm('display').setExpression('if (ch("../s_ctrl_display") == 1 && ch("../m_ctrl_display") == 1, 1, 0)')
        mid_IK.parm('display').setExpression('if (ch("../s_ctrl_display") == 1 && ch("../m_ctrl_display") == 1, 1, 0)')
        chest_IK.parm('display').setExpression('if (ch("../s_ctrl_display") == 1 && ch("../m_ctrl_display") == 1, 1, 0)')
        pelvis_ctrl.parm('display').setExpression('if (ch("../s_ctrl_display") == 1 && ch("../m_ctrl_display") == 1, 1, 0)')
        
        ##left cotnrol list
        L_ctrl_list = []
        
        ####Shoulder Control####
        ##grab the shoulder bone and root
        shoulder_bone = rig_net.node('L_shoulder_bone1')
        shoulder_root = rig_net.node('L_shoulder_root')
        ##create an fk control
        shoulder_FK = create_FK_control(shoulder_bone, 1, 'L_shoulder_FK')
        ##grab the auto and ctrl nodes frm the fk
        shoulder_ctrl = shoulder_FK[2]
        shoulder_auto = shoulder_FK[1]
        shoulder_offset = shoulder_FK[0]
        ##delete the ctrl
        shoulder_ctrl.destroy()
        ##create the stick ball ctrl
        shoulder_ctrl = create_stick_ball_null(rig_net, shoulder_auto, 'L_shoulder_FK_ctrl')
        ##set some parms to make it look nicer
        shoulder_ctrl.parmTuple('georotate').set((-20,0,-35))
        shoulder_ctrl.parm('geoscale').set(.035)
        ##reparent the ctrl
        shoulder_root.setFirstInput(chest_IK)
        shoulder_ctrl.setFirstInput(shoulder_auto)
        shoulder_offset.setFirstInput(shoulder_root)
        ##add to ctrl lists
        ctrl_list.append(shoulder_ctrl)
        L_ctrl_list.append(shoulder_ctrl)
        ##set up constraint
        simple_constraint(shoulder_bone, shoulder_ctrl)
        
        ####L arm IK FK####
        ##L arm bones
        arm_bone1 = rig_net.node('L_arm_bone1')
        arm_bone2 = rig_net.node('L_arm_bone2')
        hand_bone = rig_net.node('L_hand_bone1')
        ##create IK FK
        arm_ctrls = create_IK_FK_controls(arm_bone1, arm_bone2, shoulder_ctrl, 'L_arm', -1)
        ##extract the nodes created
        arm_ctrl1 = arm_ctrls[0]
        arm_ctrl2 = arm_ctrls[1]
        arm_twist = arm_ctrls[2]
        arm_twist_offset = rig_net.node('L_arm_twist_offset')
        arm_goal = arm_ctrls[3]
        arm_goal_offset = rig_net.node('L_arm_goal_offset')
        arm_kin = arm_ctrls[4]
        ##make controls size a bit more managable
        arm_ctrl1.parm('geoscale').set(.35)
        arm_ctrl2.parm('geoscale').set(.3)
        ##parent the IK nodes
        arm_twist_offset.setFirstInput(master)
        arm_goal_offset.setFirstInput(master)
        ##append them all to the L_side ctrls and ctrls list
        L_ctrl_list.append(arm_ctrl1)
        L_ctrl_list.append(arm_ctrl2)
        L_ctrl_list.append(arm_twist)
        L_ctrl_list.append(arm_goal)
        ctrl_list.append(arm_ctrl1)
        ctrl_list.append(arm_ctrl2)
        ctrl_list.append(arm_twist)
        ctrl_list.append(arm_goal)
        ##create hand ctrls
        hand_ctrls = create_IK_FK_controls(hand_bone, hand_bone, arm_ctrl2, 'L_hand', 1)
        ##extract the created nodes
        hand_ctrl = hand_ctrls[0]
        hand_twist = hand_ctrls[1]
        hand_twist_offset = rig_net.node('L_hand_twist_offset')
        hand_goal = hand_ctrls[2]
        hand_goal_offset = rig_net.node('L_hand_goal_offset')
        hand_kin = hand_ctrls[3]
        ##set Flags and parents so hand ik won't be seen and will simply follow the wrist IK
        hand_twist.setDisplayFlag(False)
        hand_twist.setSelectableInViewport(False)
        hand_goal.setDisplayFlag(False)
        hand_goal.setSelectableInViewport(False)
        hand_goal_offset.setFirstInput(arm_goal)
        hand_twist_offset.setFirstInput(arm_goal)
        hand_ctrl.parm('geoscale').set(.25)
        ##apend the FK ctrl
        L_ctrl_list.append(hand_ctrl)
        ctrl_list.append(hand_ctrl)
        ##set the hand kin solver to do the same as arm solver, so if one is off so is the other
        ##arm kin path
        arm_kin_blend = 'ch("' + arm_kin.path() + '/blend")'
        hand_kin.parm('blend').setExpression(arm_kin_blend)
        
        ####FINGER CONTROLS####
        ##create a null at the hand bond that will hold all the finger controls under it and follow the hand bone via constraint
        finger_grp = create_null_at_node(rig_net, hand_bone, 'finger_grp')
        ##constraing the group so it follows the hand bone whether it is in IK or FK
        simple_constraint(finger_grp, hand_bone)
        ##parent 
        finger_grp.setFirstInput(shoulder_ctrl)
        ##flags
        finger_grp.setDisplayFlag(False)
        finger_grp.setSelectableInViewport(False)
        ##grab bones
        thumb_base_bone = rig_net.node('L_thumb_bone1')
        thumb_mid_bone = rig_net.node('L_thumb_bone2')
        thumb_end_bone = rig_net.node('L_thumb_bone3')
        index_base_bone = rig_net.node('L_index_bone1')
        index_mid_bone = rig_net.node('L_index_bone2')
        index_end_bone = rig_net.node('L_index_bone3')
        middle_base_bone = rig_net.node('L_middle_bone1')
        middle_mid_bone = rig_net.node('L_middle_bone2')
        middle_end_bone = rig_net.node('L_middle_bone3')
        ring_base_bone = rig_net.node('L_ring_bone1')
        ring_mid_bone = rig_net.node('L_ring_bone2')
        ring_end_bone = rig_net.node('L_ring_bone3')
        pinky_base_bone = rig_net.node('L_pinky_bone1')
        pinky_mid_bone = rig_net.node('L_pinky_bone2')
        pinky_end_bone = rig_net.node('L_pinky_bone3')
        ##create the finger controls and constrain their bones
        thumb_base_nodes = create_FK_control(thumb_base_bone, .08, 'L_thumb_base')
        thumb_mid_nodes = create_FK_control(thumb_mid_bone, .065, 'L_thumb_mid')
        thumb_end_nodes = create_FK_control(thumb_end_bone, .05, 'L_thumb_end')
        index_base_nodes = create_FK_control(index_base_bone, .05, 'L_index_base')
        index_mid_nodes = create_FK_control(index_mid_bone, .05, 'L_index_mid')
        index_end_nodes = create_FK_control(index_end_bone, .05, 'L_index_end')
        middle_base_nodes = create_FK_control(middle_base_bone, .05, 'L_middle_base')
        middle_mid_nodes = create_FK_control(middle_mid_bone, .05, 'L_middle_mid')
        middle_end_nodes = create_FK_control(middle_end_bone, .05, 'L_middle_end')
        ring_base_nodes = create_FK_control(ring_base_bone, .05, 'L_ring_base')
        ring_mid_nodes = create_FK_control(ring_mid_bone, .05, 'L_ring_mid')
        ring_end_nodes = create_FK_control(ring_end_bone, .05, 'L_ring_end')
        pinky_base_nodes = create_FK_control(pinky_base_bone, .05, 'L_pinky_base')
        pinky_mid_nodes = create_FK_control(pinky_mid_bone, .05, 'L_pinky_mid')
        pinky_end_nodes = create_FK_control(pinky_end_bone, .05, 'L_pinky_end')
        ##extract the needed nodes
        thumb_base_offset = thumb_base_nodes[0]
        thumb_base_ctrl = thumb_base_nodes[2]
        thumb_mid_offset = thumb_mid_nodes[0]
        thumb_mid_ctrl = thumb_mid_nodes[2]
        thumb_end_offset = thumb_end_nodes[0]
        thumb_end_ctrl = thumb_end_nodes[2]
        index_base_offset = index_base_nodes[0]
        index_base_ctrl = index_base_nodes[2]
        index_mid_offset = index_mid_nodes[0]
        index_mid_ctrl = index_mid_nodes[2]
        index_end_offset = index_end_nodes[0]
        index_end_ctrl = index_end_nodes[2]
        middle_base_offset = middle_base_nodes[0]
        middle_base_ctrl = middle_base_nodes[2]
        middle_mid_offset = middle_mid_nodes[0]
        middle_mid_ctrl = middle_mid_nodes[2]
        middle_end_offset = middle_end_nodes[0]
        middle_end_ctrl = middle_end_nodes[2]
        ring_base_offset = ring_base_nodes[0]
        ring_base_ctrl = ring_base_nodes[2]
        ring_mid_offset = ring_mid_nodes[0]
        ring_mid_ctrl = ring_mid_nodes[2]
        ring_end_offset = ring_end_nodes[0]
        ring_end_ctrl = ring_end_nodes[2]
        pinky_base_offset = pinky_base_nodes[0]
        pinky_base_ctrl = pinky_base_nodes[2]
        pinky_mid_offset = pinky_mid_nodes[0]
        pinky_mid_ctrl = pinky_mid_nodes[2]
        pinky_end_offset = pinky_end_nodes[0]
        pinky_end_ctrl = pinky_end_nodes[2]
        ##set up constraints
        simple_constraint(thumb_base_bone, thumb_base_ctrl)
        simple_constraint(thumb_mid_bone, thumb_mid_ctrl)
        simple_constraint(thumb_end_bone, thumb_end_ctrl)
        simple_constraint(index_base_bone, index_base_ctrl)
        simple_constraint(index_mid_bone, index_mid_ctrl)
        simple_constraint(index_end_bone, index_end_ctrl)
        simple_constraint(middle_base_bone, middle_base_ctrl)
        simple_constraint(middle_mid_bone, middle_mid_ctrl)
        simple_constraint(middle_end_bone, middle_end_ctrl)
        simple_constraint(ring_base_bone, ring_base_ctrl)
        simple_constraint(ring_mid_bone, ring_mid_ctrl)
        simple_constraint(ring_end_bone, ring_end_ctrl)
        simple_constraint(pinky_base_bone, pinky_base_ctrl)
        simple_constraint(pinky_mid_bone, pinky_mid_ctrl)
        simple_constraint(pinky_end_bone, pinky_end_ctrl)
        ##parent in order
        thumb_base_offset.setFirstInput(finger_grp)
        thumb_mid_offset.setFirstInput(thumb_base_ctrl)
        thumb_end_offset.setFirstInput(thumb_mid_ctrl)
        index_base_offset.setFirstInput(finger_grp)
        index_mid_offset.setFirstInput(index_base_ctrl)
        index_end_offset.setFirstInput(index_mid_ctrl)
        middle_base_offset.setFirstInput(finger_grp)
        middle_mid_offset.setFirstInput(middle_base_ctrl)
        middle_end_offset.setFirstInput(middle_mid_ctrl)
        ring_base_offset.setFirstInput(finger_grp)
        ring_mid_offset.setFirstInput(ring_base_ctrl)
        ring_end_offset.setFirstInput(ring_mid_ctrl)
        pinky_base_offset.setFirstInput(finger_grp)
        pinky_mid_offset.setFirstInput(pinky_base_ctrl)
        pinky_end_offset.setFirstInput(pinky_mid_ctrl)
        ##apend to lists
        ctrl_list.append(thumb_base_ctrl)
        L_ctrl_list.append(thumb_base_ctrl)
        ctrl_list.append(thumb_mid_ctrl)
        L_ctrl_list.append(thumb_mid_ctrl)
        ctrl_list.append(thumb_end_ctrl)
        L_ctrl_list.append(thumb_end_ctrl)
        ctrl_list.append(index_base_ctrl)
        L_ctrl_list.append(index_base_ctrl)
        ctrl_list.append(index_mid_ctrl)
        L_ctrl_list.append(index_mid_ctrl)
        ctrl_list.append(index_end_ctrl)
        L_ctrl_list.append(index_end_ctrl)
        ctrl_list.append(middle_base_ctrl)
        L_ctrl_list.append(middle_base_ctrl)
        ctrl_list.append(middle_mid_ctrl)
        L_ctrl_list.append(middle_mid_ctrl)
        ctrl_list.append(middle_end_ctrl)
        L_ctrl_list.append(middle_end_ctrl)
        ctrl_list.append(ring_base_ctrl)
        L_ctrl_list.append(ring_base_ctrl)
        ctrl_list.append(ring_mid_ctrl)
        L_ctrl_list.append(ring_mid_ctrl)
        ctrl_list.append(ring_end_ctrl)
        L_ctrl_list.append(ring_end_ctrl)
        ctrl_list.append(pinky_base_ctrl)
        L_ctrl_list.append(pinky_base_ctrl)
        ctrl_list.append(pinky_mid_ctrl)
        L_ctrl_list.append(pinky_mid_ctrl)
        ctrl_list.append(pinky_end_ctrl)
        L_ctrl_list.append(pinky_end_ctrl)
        
        ####ARM AND HAND UI#####
        ##grab the hda parmTemplateGroup
        rig_ptg = rig_net.parmTemplateGroup()
        ##create arm folder
        arm_folder = hou.FolderParmTemplate('L_arm_folder', 'L Arm')
        
        ##create the needed folders in master folder
        arm_display_folder = hou.FolderParmTemplate('L_arm_display_folder', 'Display')
        arm_action_folder = hou.FolderParmTemplate('L_arm_action_folder', 'Actions')
        arm_ctrl_folder = hou.FolderParmTemplate('L_arm_ctrl_folder', 'Controls')
        ##change to simple
        arm_display_folder.setFolderType(hou.folderType.Simple)
        arm_action_folder.setFolderType(hou.folderType.Simple)
        arm_ctrl_folder.setFolderType(hou.folderType.Simple)
        
        ##create the needed menu parameters to the display folder
        arm_bone_display = hou.MenuParmTemplate('L_arm_bone_display', 'Bone Display', ['0', '1'], ['OFF', 'ON'], 0)
        arm_ctrl_dispaly = hou.MenuParmTemplate('L_arm_ctrl_display', 'Controls Display', ['0', '1'], ['OFF', 'ON'], 1)
        ##add to the folder
        arm_display_folder.addParmTemplate(arm_bone_display)
        arm_display_folder.addParmTemplate(arm_ctrl_dispaly)
        ##add folder to arm_folder
        arm_folder.addParmTemplate(arm_display_folder)
        
        ##create buttons for the actions folder
        arm_default = hou.ButtonParmTemplate('set_L_arm_to_default', 'Set L Arm to Default')
        arm_key = hou.ButtonParmTemplate('set_L_arm_key', 'Set L Arm Keys')
        ##add the buttons to the actions folder
        arm_action_folder.addParmTemplate(arm_default)
        arm_action_folder.addParmTemplate(arm_key)
        ##add the action folder to the master folder
        arm_folder.addParmTemplate(arm_action_folder)
        
        ##create floats for the control
        arm_FK_IK = hou.FloatParmTemplate('L_arm_FK_IK', 'L Arm FK|IK', 1, [1], 0, 1, True, True)
        shoulder_rot = hou.FloatParmTemplate('L_shoulder_rot', 'L Shoulder Rotate', 3)
        arm_IK_trans = hou.FloatParmTemplate('L_arm_IK_trans', 'L Arm IK Translate', 3)
        arm_IK_rot = hou.FloatParmTemplate('L_arm_IK_rot', 'L Arm IK Rotate', 3)
        arm_twist_trans = hou.FloatParmTemplate('L_arm_twist_trans', 'L Arm Twist Translate', 3)
        arm_bone1_FK = hou.FloatParmTemplate('L_arm_bone1_FK_rot', 'L Arm Bone1 FK Rotate', 3)
        arm_bone2_FK = hou.FloatParmTemplate('L_arm_bone2_FK_rot', 'L Arm Bone2 FK Rotate', 3)
        hand_FK = hou.FloatParmTemplate('L_hand_FK_rot', 'L Hand FK Rotate', 3)
        ##add the floats to the control folder
        arm_ctrl_folder.addParmTemplate(arm_FK_IK)
        arm_ctrl_folder.addParmTemplate(shoulder_rot)
        arm_ctrl_folder.addParmTemplate(arm_IK_trans)
        arm_ctrl_folder.addParmTemplate(arm_IK_rot)
        arm_ctrl_folder.addParmTemplate(arm_twist_trans)
        arm_ctrl_folder.addParmTemplate(arm_bone1_FK)
        arm_ctrl_folder.addParmTemplate(arm_bone2_FK)
        arm_ctrl_folder.addParmTemplate(hand_FK)
        ##add the ctrl folder to master
        arm_folder.addParmTemplate(arm_ctrl_folder)
        
        ##create hand folder
        hand_folder = hou.FolderParmTemplate('L_hand_folder', 'L hand')
        hand_folder.setFolderType(hou.folderType.Simple)
        
        ##create the needed folders in master folder
        hand_action_folder = hou.FolderParmTemplate('L_hand_action_folder', 'Actions')
        ##change to simple
        hand_action_folder.setFolderType(hou.folderType.Simple)
        
        ##create the needed menu parameters to the display folder
        hand_bone_display = hou.MenuParmTemplate('L_hand_bone_display', 'Bone Display', ['0', '1'], ['OFF', 'ON'], 0)
        hand_ctrl_dispaly = hou.MenuParmTemplate('L_hand_ctrl_display', 'Controls Display', ['0', '1'], ['OFF', 'ON'], 1)
        ##add to the folder
        hand_folder.addParmTemplate(hand_bone_display)
        hand_folder.addParmTemplate(hand_ctrl_dispaly)
        
        ##create buttons for the actions folder
        hand_default = hou.ButtonParmTemplate('set_L_hand_to_default', 'Set L hand to Default')
        hand_key = hou.ButtonParmTemplate('set_L_hand_key', 'Set L hand Keys')
        ##add the buttons to the actions folder
        hand_action_folder.addParmTemplate(hand_default)
        hand_action_folder.addParmTemplate(hand_key)
        ##add the action folder to the master folder
        hand_folder.addParmTemplate(hand_action_folder)
        
        ##create floats for specail hand quick poses WIP
        
        ##add the floats to the hand folder
        
        ##create a folder for each finger
        thumb_folder = hou.FolderParmTemplate('L_thumb_folder', 'L Thumb')
        index_folder = hou.FolderParmTemplate('L_index_folder', 'L Index')
        middle_folder = hou.FolderParmTemplate('L_middle_folder', 'L Middle')
        ring_folder = hou.FolderParmTemplate('L_ring_folder', 'L Ring')
        pinky_folder = hou.FolderParmTemplate('L_pinky_folder', 'L Pinky')
        ##create floats for rotation and quick pose(WIP)
        thumb_base_rot = hou.FloatParmTemplate('L_thumb_base_rot', 'L Thumb Base Rotate', 3)
        thumb_mid_rot = hou.FloatParmTemplate('L_thumb_mid_rot', 'L Thumb Mid Rotate', 3)
        thumb_end_rot = hou.FloatParmTemplate('L_thumb_end_rot', 'L Thumb End Rotate', 3)
        index_base_rot = hou.FloatParmTemplate('L_index_base_rot', 'L Index Base Rotate', 3)
        index_mid_rot = hou.FloatParmTemplate('L_index_mid_rot', 'L Index Mid Rotate', 3)
        index_end_rot = hou.FloatParmTemplate('L_index_end_rot', 'L Index End Rotate', 3)
        middle_base_rot = hou.FloatParmTemplate('L_middle_base_rot', 'L Middle Base Rotate', 3)
        middle_mid_rot = hou.FloatParmTemplate('L_middle_mid_rot', 'L Middle Mid Rotate', 3)
        middle_end_rot = hou.FloatParmTemplate('L_middle_end_rot', 'L Middle End Rotate', 3)
        ring_base_rot = hou.FloatParmTemplate('L_ring_base_rot', 'L Ring Base Rotate', 3)
        ring_mid_rot = hou.FloatParmTemplate('L_ring_mid_rot', 'L Ring Mid Rotate', 3)
        ring_end_rot = hou.FloatParmTemplate('L_ring_end_rot', 'L Ring End Rotate', 3)
        pinky_base_rot = hou.FloatParmTemplate('L_pinky_base_rot', 'L Pinky Base Rotate', 3)
        pinky_mid_rot = hou.FloatParmTemplate('L_pinky_mid_rot', 'L Pinky Mid Rotate', 3)
        pinky_end_rot = hou.FloatParmTemplate('L_pinky_end_rot', 'L Pinky End Rotate', 3)
        ##add the floats to the folders
        thumb_folder.addParmTemplate(thumb_base_rot)
        thumb_folder.addParmTemplate(thumb_mid_rot)
        thumb_folder.addParmTemplate(thumb_end_rot)
        index_folder.addParmTemplate(index_base_rot)
        index_folder.addParmTemplate(index_mid_rot)
        index_folder.addParmTemplate(index_end_rot)
        middle_folder.addParmTemplate(middle_base_rot)
        middle_folder.addParmTemplate(middle_mid_rot)
        middle_folder.addParmTemplate(middle_end_rot)
        ring_folder.addParmTemplate(ring_base_rot)
        ring_folder.addParmTemplate(ring_mid_rot)
        ring_folder.addParmTemplate(ring_end_rot)
        pinky_folder.addParmTemplate(pinky_base_rot)
        pinky_folder.addParmTemplate(pinky_mid_rot)
        pinky_folder.addParmTemplate(pinky_end_rot)
        ##add folders to hand folder
        hand_folder.addParmTemplate(thumb_folder)
        hand_folder.addParmTemplate(index_folder)
        hand_folder.addParmTemplate(middle_folder)
        hand_folder.addParmTemplate(ring_folder)
        hand_folder.addParmTemplate(pinky_folder)
        ##add hand folder to arm folder
        arm_folder.addParmTemplate(hand_folder)
        
        ##add the spine folder to the template group
        rig_ptg.addParmTemplate(arm_folder)
        ##reset the rig_net template back to the copy we have been editing
        rig_net.setParmTemplateGroup(rig_ptg)
        
        ####ARM UI INTEGRATION####
        arm_kin.parm('blend').setExpression('ch("../../L_arm_FK_IK")')
        shoulder_ctrl.parm('rx').setExpression('ch("../L_shoulder_rotx")')
        shoulder_ctrl.parm('ry').setExpression('ch("../L_shoulder_roty")')
        shoulder_ctrl.parm('rz').setExpression('ch("../L_shoulder_rotz")')
        arm_goal.parm('tx').setExpression('ch("../L_arm_IK_transx")')
        arm_goal.parm('ty').setExpression('ch("../L_arm_IK_transy")')
        arm_goal.parm('tz').setExpression('ch("../L_arm_IK_transz")')
        arm_goal.parm('rx').setExpression('ch("../L_arm_IK_rotx")')
        arm_goal.parm('ry').setExpression('ch("../L_arm_IK_roty")')
        arm_goal.parm('rz').setExpression('ch("../L_arm_IK_rotz")')
        arm_twist.parm('tx').setExpression('ch("../L_arm_twist_transx")')
        arm_twist.parm('ty').setExpression('ch("../L_arm_twist_transy")')
        arm_twist.parm('tz').setExpression('ch("../L_arm_twist_transz")')
        arm_ctrl1.parm('rx').setExpression('ch("../L_arm_bone1_FK_rotx")')
        arm_ctrl1.parm('ry').setExpression('ch("../L_arm_bone1_FK_roty")')
        arm_ctrl1.parm('rz').setExpression('ch("../L_arm_bone1_FK_rotz")')
        arm_ctrl2.parm('rx').setExpression('ch("../L_arm_bone2_FK_rotx")')
        arm_ctrl2.parm('ry').setExpression('ch("../L_arm_bone2_FK_roty")')
        arm_ctrl2.parm('rz').setExpression('ch("../L_arm_bone2_FK_rotz")')
        hand_ctrl.parm('rx').setExpression('ch("../L_hand_FK_rotx")')
        hand_ctrl.parm('ry').setExpression('ch("../L_hand_FK_roty")')
        hand_ctrl.parm('rz').setExpression('ch("../L_hand_FK_rotz")')
        thumb_base_ctrl.parm('rx').setExpression('ch("../L_thumb_base_rotx")')
        thumb_base_ctrl.parm('ry').setExpression('ch("../L_thumb_base_roty")')
        thumb_base_ctrl.parm('rz').setExpression('ch("../L_thumb_base_rotz")')
        thumb_mid_ctrl.parm('rx').setExpression('ch("../L_thumb_mid_rotx")')
        thumb_mid_ctrl.parm('ry').setExpression('ch("../L_thumb_mid_roty")')
        thumb_mid_ctrl.parm('rz').setExpression('ch("../L_thumb_mid_rotz")')
        thumb_end_ctrl.parm('rx').setExpression('ch("../L_thumb_end_rotx")')
        thumb_end_ctrl.parm('ry').setExpression('ch("../L_thumb_end_roty")')
        thumb_end_ctrl.parm('rz').setExpression('ch("../L_thumb_end_rotz")')
        index_base_ctrl.parm('rx').setExpression('ch("../L_index_base_rotx")')
        index_base_ctrl.parm('ry').setExpression('ch("../L_index_base_roty")')
        index_base_ctrl.parm('rz').setExpression('ch("../L_index_base_rotz")')
        index_mid_ctrl.parm('rx').setExpression('ch("../L_index_mid_rotx")')
        index_mid_ctrl.parm('ry').setExpression('ch("../L_index_mid_roty")')
        index_mid_ctrl.parm('rz').setExpression('ch("../L_index_mid_rotz")')
        index_end_ctrl.parm('rx').setExpression('ch("../L_index_end_rotx")')
        index_end_ctrl.parm('ry').setExpression('ch("../L_index_end_roty")')
        index_end_ctrl.parm('rz').setExpression('ch("../L_index_end_rotz")')
        middle_base_ctrl.parm('rx').setExpression('ch("../L_middle_base_rotx")')
        middle_base_ctrl.parm('ry').setExpression('ch("../L_middle_base_roty")')
        middle_base_ctrl.parm('rz').setExpression('ch("../L_middle_base_rotz")')
        middle_mid_ctrl.parm('rx').setExpression('ch("../L_middle_mid_rotx")')
        middle_mid_ctrl.parm('ry').setExpression('ch("../L_middle_mid_roty")')
        middle_mid_ctrl.parm('rz').setExpression('ch("../L_middle_mid_rotz")')
        middle_end_ctrl.parm('rx').setExpression('ch("../L_middle_end_rotx")')
        middle_end_ctrl.parm('ry').setExpression('ch("../L_middle_end_roty")')
        middle_end_ctrl.parm('rz').setExpression('ch("../L_middle_end_rotz")')
        ring_base_ctrl.parm('rx').setExpression('ch("../L_ring_base_rotx")')
        ring_base_ctrl.parm('ry').setExpression('ch("../L_ring_base_roty")')
        ring_base_ctrl.parm('rz').setExpression('ch("../L_ring_base_rotz")')
        ring_mid_ctrl.parm('rx').setExpression('ch("../L_ring_mid_rotx")')
        ring_mid_ctrl.parm('ry').setExpression('ch("../L_ring_mid_roty")')
        ring_mid_ctrl.parm('rz').setExpression('ch("../L_ring_mid_rotz")')
        ring_end_ctrl.parm('rx').setExpression('ch("../L_ring_end_rotx")')
        ring_end_ctrl.parm('ry').setExpression('ch("../L_ring_end_roty")')
        ring_end_ctrl.parm('rz').setExpression('ch("../L_ring_end_rotz")')
        pinky_base_ctrl.parm('rx').setExpression('ch("../L_pinky_base_rotx")')
        pinky_base_ctrl.parm('ry').setExpression('ch("../L_pinky_base_roty")')
        pinky_base_ctrl.parm('rz').setExpression('ch("../L_pinky_base_rotz")')
        pinky_mid_ctrl.parm('rx').setExpression('ch("../L_pinky_mid_rotx")')
        pinky_mid_ctrl.parm('ry').setExpression('ch("../L_pinky_mid_roty")')
        pinky_mid_ctrl.parm('rz').setExpression('ch("../L_pinky_mid_rotz")')
        pinky_end_ctrl.parm('rx').setExpression('ch("../L_pinky_end_rotx")')
        pinky_end_ctrl.parm('ry').setExpression('ch("../L_pinky_end_roty")')
        pinky_end_ctrl.parm('rz').setExpression('ch("../L_pinky_end_rotz")')
        
        ##displayability options implementation
        ##bones
        ##if master bone display and arm bone display are on than set value 1, else 0
        rig_net.node('L_shoulder_bone1').parm('tdisplay').set(True)
        rig_net.node('L_arm_bone1').parm('tdisplay').set(True)
        rig_net.node('L_arm_bone2').parm('tdisplay').set(True)
        rig_net.node('L_hand_bone1').parm('tdisplay').set(True)
        rig_net.node('L_shoulder_bone1').parm('display').setExpression('if (ch("../L_arm_bone_display") == 1 && ch("../m_bone_display") == 1, 1, 0)')
        rig_net.node('L_arm_bone1').parm('display').setExpression('if (ch("../L_arm_bone_display") == 1 && ch("../m_bone_display") == 1, 1, 0)')
        rig_net.node('L_arm_bone2').parm('display').setExpression('if (ch("../L_arm_bone_display") == 1 && ch("../m_bone_display") == 1, 1, 0)')
        rig_net.node('L_hand_bone1').parm('display').setExpression('if (ch("../L_arm_bone_display") == 1 && ch("../m_bone_display") == 1, 1, 0)')
        rig_net.node('L_thumb_bone1').parm('tdisplay').set(True)
        rig_net.node('L_thumb_bone2').parm('tdisplay').set(True)
        rig_net.node('L_thumb_bone3').parm('tdisplay').set(True)
        rig_net.node('L_index_bone1').parm('tdisplay').set(True)
        rig_net.node('L_index_bone2').parm('tdisplay').set(True)
        rig_net.node('L_index_bone3').parm('tdisplay').set(True)
        rig_net.node('L_middle_bone1').parm('tdisplay').set(True)
        rig_net.node('L_middle_bone2').parm('tdisplay').set(True)
        rig_net.node('L_middle_bone3').parm('tdisplay').set(True)
        rig_net.node('L_ring_bone1').parm('tdisplay').set(True)
        rig_net.node('L_ring_bone2').parm('tdisplay').set(True)
        rig_net.node('L_ring_bone3').parm('tdisplay').set(True)
        rig_net.node('L_pinky_bone1').parm('tdisplay').set(True)
        rig_net.node('L_pinky_bone2').parm('tdisplay').set(True)
        rig_net.node('L_pinky_bone3').parm('tdisplay').set(True)
        rig_net.node('L_thumb_bone1').parm('display').setExpression('if (ch("../L_hand_bone_display") == 1 && ch("../m_bone_display") == 1, 1, 0)')
        rig_net.node('L_thumb_bone2').parm('display').setExpression('if (ch("../L_hand_bone_display") == 1 && ch("../m_bone_display") == 1, 1, 0)')
        rig_net.node('L_thumb_bone3').parm('display').setExpression('if (ch("../L_hand_bone_display") == 1 && ch("../m_bone_display") == 1, 1, 0)')
        rig_net.node('L_index_bone1').parm('display').setExpression('if (ch("../L_hand_bone_display") == 1 && ch("../m_bone_display") == 1, 1, 0)')
        rig_net.node('L_index_bone2').parm('display').setExpression('if (ch("../L_hand_bone_display") == 1 && ch("../m_bone_display") == 1, 1, 0)')
        rig_net.node('L_index_bone3').parm('display').setExpression('if (ch("../L_hand_bone_display") == 1 && ch("../m_bone_display") == 1, 1, 0)')
        rig_net.node('L_middle_bone1').parm('display').setExpression('if (ch("../L_hand_bone_display") == 1 && ch("../m_bone_display") == 1, 1, 0)')
        rig_net.node('L_middle_bone2').parm('display').setExpression('if (ch("../L_hand_bone_display") == 1 && ch("../m_bone_display") == 1, 1, 0)')
        rig_net.node('L_middle_bone3').parm('display').setExpression('if (ch("../L_hand_bone_display") == 1 && ch("../m_bone_display") == 1, 1, 0)')
        rig_net.node('L_ring_bone1').parm('display').setExpression('if (ch("../L_hand_bone_display") == 1 && ch("../m_bone_display") == 1, 1, 0)')
        rig_net.node('L_ring_bone2').parm('display').setExpression('if (ch("../L_hand_bone_display") == 1 && ch("../m_bone_display") == 1, 1, 0)')
        rig_net.node('L_ring_bone3').parm('display').setExpression('if (ch("../L_hand_bone_display") == 1 && ch("../m_bone_display") == 1, 1, 0)')
        rig_net.node('L_pinky_bone1').parm('display').setExpression('if (ch("../L_hand_bone_display") == 1 && ch("../m_bone_display") == 1, 1, 0)')
        rig_net.node('L_pinky_bone2').parm('display').setExpression('if (ch("../L_hand_bone_display") == 1 && ch("../m_bone_display") == 1, 1, 0)')
        rig_net.node('L_pinky_bone3').parm('display').setExpression('if (ch("../L_hand_bone_display") == 1 && ch("../m_bone_display") == 1, 1, 0)')
        ##Ctrls
        shoulder_ctrl.parm('tdisplay').set(True)
        arm_goal.parm('tdisplay').set(True)
        arm_twist.parm('tdisplay').set(True)
        arm_ctrl1.parm('tdisplay').set(True)
        arm_ctrl2.parm('tdisplay').set(True)
        hand_ctrl.parm('tdisplay').set(True)
        thumb_base_ctrl.parm('tdisplay').set(True)
        thumb_mid_ctrl.parm('tdisplay').set(True)
        thumb_end_ctrl.parm('tdisplay').set(True)
        index_base_ctrl.parm('tdisplay').set(True)
        index_mid_ctrl.parm('tdisplay').set(True)
        index_end_ctrl.parm('tdisplay').set(True)
        middle_base_ctrl.parm('tdisplay').set(True)
        middle_mid_ctrl.parm('tdisplay').set(True)
        middle_end_ctrl.parm('tdisplay').set(True)
        ring_base_ctrl.parm('tdisplay').set(True)
        ring_mid_ctrl.parm('tdisplay').set(True)
        ring_end_ctrl.parm('tdisplay').set(True)
        pinky_base_ctrl.parm('tdisplay').set(True)
        pinky_mid_ctrl.parm('tdisplay').set(True)
        pinky_end_ctrl.parm('tdisplay').set(True)
        shoulder_ctrl.parm('display').setExpression('if (ch("../L_arm_ctrl_display") == 1 && ch("../m_ctrl_display") == 1, 1, 0)')
        arm_goal.parm('display').setExpression('if (ch("../L_arm_ctrl_display") == 1 && ch("../m_ctrl_display") == 1 && ch("../L_arm_FK_IK") == 1, 1, 0)')
        arm_twist.parm('display').setExpression('if (ch("../L_arm_ctrl_display") == 1 && ch("../m_ctrl_display") == 1 && ch("../L_arm_FK_IK") == 1, 1, 0)')
        arm_ctrl1.parm('display').setExpression('if (ch("../L_arm_ctrl_display") == 1 && ch("../m_ctrl_display") == 1 && ch("../L_arm_FK_IK") == 0, 1, 0)')
        arm_ctrl2.parm('display').setExpression('if (ch("../L_arm_ctrl_display") == 1 && ch("../m_ctrl_display") == 1 && ch("../L_arm_FK_IK") == 0, 1, 0)')
        hand_ctrl.parm('display').setExpression('if (ch("../L_arm_ctrl_display") == 1 && ch("../m_ctrl_display") == 1 && ch("../L_arm_FK_IK") == 0, 1, 0)')
        thumb_base_ctrl.parm('display').setExpression('if (ch("../L_hand_ctrl_display") == 1 && ch("../m_ctrl_display") == 1, 1, 0)')
        thumb_mid_ctrl.parm('display').setExpression('if (ch("../L_hand_ctrl_display") == 1 && ch("../m_ctrl_display") == 1, 1, 0)')
        thumb_end_ctrl.parm('display').setExpression('if (ch("../L_hand_ctrl_display") == 1 && ch("../m_ctrl_display") == 1, 1, 0)')
        index_base_ctrl.parm('display').setExpression('if (ch("../L_hand_ctrl_display") == 1 && ch("../m_ctrl_display") == 1, 1, 0)')
        index_mid_ctrl.parm('display').setExpression('if (ch("../L_hand_ctrl_display") == 1 && ch("../m_ctrl_display") == 1, 1, 0)')
        index_end_ctrl.parm('display').setExpression('if (ch("../L_hand_ctrl_display") == 1 && ch("../m_ctrl_display") == 1, 1, 0)')
        middle_base_ctrl.parm('display').setExpression('if (ch("../L_hand_ctrl_display") == 1 && ch("../m_ctrl_display") == 1, 1, 0)')
        middle_mid_ctrl.parm('display').setExpression('if (ch("../L_hand_ctrl_display") == 1 && ch("../m_ctrl_display") == 1, 1, 0)')
        middle_end_ctrl.parm('display').setExpression('if (ch("../L_hand_ctrl_display") == 1 && ch("../m_ctrl_display") == 1, 1, 0)')
        ring_base_ctrl.parm('display').setExpression('if (ch("../L_hand_ctrl_display") == 1 && ch("../m_ctrl_display") == 1, 1, 0)')
        ring_mid_ctrl.parm('display').setExpression('if (ch("../L_hand_ctrl_display") == 1 && ch("../m_ctrl_display") == 1, 1, 0)')
        ring_end_ctrl.parm('display').setExpression('if (ch("../L_hand_ctrl_display") == 1 && ch("../m_ctrl_display") == 1, 1, 0)')
        pinky_base_ctrl.parm('display').setExpression('if (ch("../L_hand_ctrl_display") == 1 && ch("../m_ctrl_display") == 1, 1, 0)')
        pinky_mid_ctrl.parm('display').setExpression('if (ch("../L_hand_ctrl_display") == 1 && ch("../m_ctrl_display") == 1, 1, 0)')
        pinky_end_ctrl.parm('display').setExpression('if (ch("../L_hand_ctrl_display") == 1 && ch("../m_ctrl_display") == 1, 1, 0)')
        
        ####LEG COTNROLS####
        ##grab the bones
        leg_bone1 = rig_net.node('L_leg_bone1')
        leg_bone2 = rig_net.node('L_leg_bone2')
        foot_bone1 = rig_net.node('L_foot_bone1')
        foot_bone2 = rig_net.node('L_foot_bone2')
        ##create IK FK for leg
        leg_nodes = create_IK_FK_controls(leg_bone1, leg_bone2, pelvis_ctrl, 'L_leg', -1)
        ##extract nodes
        leg_ctrl1 = leg_nodes[0]
        leg_ctrl2 = leg_nodes[1]
        leg_twist = leg_nodes[2]
        leg_twist_offset = rig_net.node('L_leg_twist_offset')
        leg_goal = leg_nodes[3]
        leg_goal_offset = rig_net.node('L_leg_goal_offset')
        leg_kin = leg_nodes[4]
        ##correct the rotation of the foot IK goal. MY IK FK creates a goal alligned with the end_bone at the end of it,
        ##we don't want that in this case, we want it alligned with the world
        leg_goal_offset.parmTuple('r').set((0,0,0))
        ###create first foot bone controls
        foot_nodes = create_IK_FK_controls(foot_bone1, foot_bone1, leg_ctrl2, 'L_foot', 1)
        ##extract nodes
        foot_ctrl = foot_nodes[0]
        foot_twist = foot_nodes[1]
        foot_twist_offset = rig_net.node('L_foot_twist_offset')
        foot_goal = foot_nodes[2]
        foot_goal_offset = rig_net.node('L_foot_goal_offset')
        foot_kin = foot_nodes[3]
        ##set flags
        foot_twist.setDisplayFlag(False)
        foot_twist.setSelectableInViewport(False)
        foot_goal.setDisplayFlag(False)
        foot_goal.setSelectableInViewport(False)
        ##create secton foot bone (Toe) controls
        toe_nodes = create_IK_FK_controls(foot_bone2, foot_bone2, foot_ctrl, 'L_toe', 1)
        ##extract the nodes
        toe_ctrl = toe_nodes[0]
        toe_twist = toe_nodes[1]
        toe_twist_offset = rig_net.node('L_toe_twist_offset')
        toe_goal = toe_nodes[2]
        toe_goal_offset = rig_net.node('L_toe_goal_offset')
        toe_kin = toe_nodes[3]
        ##set flags
        toe_twist.setDisplayFlag(False)
        toe_twist.setSelectableInViewport(False)
        toe_goal.setDisplayFlag(False)
        toe_goal.setSelectableInViewport(False)
        ##set the foot kin to follow whatever the leg kin does
        leg_kin_blend = 'ch("' + leg_kin.path() + '/blend")'
        foot_kin.parm('blend').setExpression(leg_kin_blend)
        toe_kin.parm('blend').setExpression(leg_kin_blend)
        ##set some display parms so its a bit prettier in FK
        foot_ctrl.parm('geoscale').set(.3)
        foot_ctrl.parm('georotatex').set(-40)
        toe_ctrl.parm('geoscale').set(.3)
        toe_ctrl.parm('geosizey').set(.6)
        ##append controls to lists
        ctrl_list.append(leg_ctrl1)
        L_ctrl_list.append(leg_ctrl1)
        ctrl_list.append(leg_ctrl2)
        L_ctrl_list.append(leg_ctrl2)
        ctrl_list.append(leg_twist)
        L_ctrl_list.append(leg_twist)
        ctrl_list.append(leg_goal)
        L_ctrl_list.append(leg_goal)
        ctrl_list.append(foot_ctrl)
        L_ctrl_list.append(foot_ctrl)
        ctrl_list.append(toe_ctrl)
        L_ctrl_list.append(toe_ctrl)
        ##create roll nodes
        ##grab foot locators
        toe_loc = rig_net.node('L_toe_tip_locator')
        ball_loc = rig_net.node('L_ball_locator')
        heel_loc = rig_net.node('L_heel_locator')
        outer_loc = rig_net.node('L_foot_outer_locator')
        inner_loc = rig_net.node('L_foot_inner_locator')
        ##create new nulls
        toe_roll = create_null_at_node(rig_net, toe_loc, 'toe_roll')
        ball_roll = create_null_at_node(rig_net, ball_loc, 'ball_roll')
        heel_roll = create_null_at_node(rig_net, heel_loc, 'heel_roll')
        outer_roll = create_null_at_node(rig_net, outer_loc, 'outer_roll')
        inner_roll = create_null_at_node(rig_net, inner_loc, 'inner_roll')
        ##set flags
        toe_roll.setDisplayFlag(False)
        toe_roll.setSelectableInViewport(False)
        ball_roll.setDisplayFlag(False)
        ball_roll.setSelectableInViewport(False)
        heel_roll.setDisplayFlag(False)
        heel_roll.setSelectableInViewport(False)
        outer_roll.setDisplayFlag(False)
        outer_roll.setSelectableInViewport(False)
        inner_roll.setDisplayFlag(False)
        inner_roll.setSelectableInViewport(False)
        ##grab the leg_goal node
        leg_IK_goal = rig_net.node('L_leg_goal_loc')
        ##set up parents
        leg_twist_offset.setFirstInput(master)
        leg_goal_offset.setFirstInput(master)
        heel_roll.setFirstInput(leg_goal)
        toe_roll.setFirstInput(heel_roll)
        outer_roll.setFirstInput(toe_roll)
        inner_roll.setFirstInput(outer_roll)
        ball_roll.setFirstInput(inner_roll)
        leg_IK_goal.setFirstInput(ball_roll)
        foot_goal_offset.setFirstInput(ball_roll)
        foot_twist_offset.setFirstInput(ball_roll)
        toe_goal_offset.setFirstInput(inner_roll)
        toe_twist_offset.setFirstInput(inner_roll)
        ##clean transforms
        toe_roll.moveParmTransformIntoPreTransform()
        ball_roll.moveParmTransformIntoPreTransform()
        heel_roll.moveParmTransformIntoPreTransform()
        outer_roll.moveParmTransformIntoPreTransform()
        inner_roll.moveParmTransformIntoPreTransform()
        
        ####LEG UI####
        ##grab the hda parmTemplateGroup
        rig_ptg = rig_net.parmTemplateGroup()
        ##create arm folder
        leg_folder = hou.FolderParmTemplate('L_leg_folder', 'L Leg')
        
        ##create the needed folders in master folder
        leg_display_folder = hou.FolderParmTemplate('L_leg_display_folder', 'Display')
        leg_action_folder = hou.FolderParmTemplate('L_leg_action_folder', 'Actions')
        leg_ctrl_folder = hou.FolderParmTemplate('L_leg_ctrl_folder', 'Controls')
        ##change to simple
        leg_display_folder.setFolderType(hou.folderType.Simple)
        leg_action_folder.setFolderType(hou.folderType.Simple)
        leg_ctrl_folder.setFolderType(hou.folderType.Simple)
        
        ##create the needed menu parameters to the display folder
        leg_bone_display = hou.MenuParmTemplate('L_leg_bone_display', 'Bone Display', ['0', '1'], ['OFF', 'ON'], 0)
        leg_ctrl_dispaly = hou.MenuParmTemplate('L_leg_ctrl_display', 'Controls Display', ['0', '1'], ['OFF', 'ON'], 1)
        ##add to the folder
        leg_display_folder.addParmTemplate(leg_bone_display)
        leg_display_folder.addParmTemplate(leg_ctrl_dispaly)
        ##add folder to leg_folder
        leg_folder.addParmTemplate(leg_display_folder)
        
        ##create buttons for the actions folder
        leg_default = hou.ButtonParmTemplate('set_L_leg_to_default', 'Set L Leg to Default')
        leg_key = hou.ButtonParmTemplate('set_L_leg_key', 'Set L Leg Keys')
        ##add the buttons to the actions folder
        leg_action_folder.addParmTemplate(leg_default)
        leg_action_folder.addParmTemplate(leg_key)
        ##add the action folder to the master folder
        leg_folder.addParmTemplate(leg_action_folder)
        
        ##create floats for the control
        leg_FK_IK = hou.FloatParmTemplate('L_leg_FK_IK', 'L Leg FK|IK', 1, [1], 0, 1, True, True)
        leg_IK_trans = hou.FloatParmTemplate('L_leg_IK_trans', 'L Leg IK Translate', 3)
        leg_IK_rot = hou.FloatParmTemplate('L_leg_IK_rot', 'L Leg IK Rotate', 3)
        leg_twist_trans = hou.FloatParmTemplate('L_leg_twist_trans', 'L Leg Twist Translate', 3)
        leg_bone1_FK = hou.FloatParmTemplate('L_leg_bone1_FK_rot', 'L Leg Bone1 FK Rotate', 3)
        leg_bone2_FK = hou.FloatParmTemplate('L_leg_bone2_FK_rot', 'L Leg Bone2 FK Rotate', 3)
        foot_FK = hou.FloatParmTemplate('L_foot_FK_rot', 'L Foot FK Rotate', 3)
        toe_FK = hou.FloatParmTemplate('L_toe_FK_rot', 'L Toe FK Rotate', 3)
        ##add the floats to the control folder
        leg_ctrl_folder.addParmTemplate(leg_FK_IK)
        leg_ctrl_folder.addParmTemplate(leg_IK_trans)
        leg_ctrl_folder.addParmTemplate(leg_IK_rot)
        leg_ctrl_folder.addParmTemplate(leg_twist_trans)
        leg_ctrl_folder.addParmTemplate(leg_bone1_FK)
        leg_ctrl_folder.addParmTemplate(leg_bone2_FK)
        leg_ctrl_folder.addParmTemplate(foot_FK)
        leg_ctrl_folder.addParmTemplate(toe_FK)
        ##add the ctrl folder to master
        leg_folder.addParmTemplate(leg_ctrl_folder)
        
        ##create hand folder
        foot_folder = hou.FolderParmTemplate('L_foot_folder', 'L Foot IK')
        foot_folder.setFolderType(hou.folderType.Simple)
        
        ##create buttons for the actions folder
        foot_default = hou.ButtonParmTemplate('set_L_foot_to_default', 'Set L foot to Default')
        foot_key = hou.ButtonParmTemplate('set_L_foot_key', 'Set L foot Keys')
        ##add the buttons to the actions folder
        foot_folder.addParmTemplate(foot_default)
        foot_folder.addParmTemplate(foot_key)
        ##create floats different rolls
        toe_roll_rot = hou.FloatParmTemplate('L_toe_roll_rot', 'L Toe Roll Rotate', 1, [0], 0, 10, True, True)
        toe_twist_rot = hou.FloatParmTemplate('L_toe_twist_rot', 'L Toe Twist Rotate', 1, [0], -10, 10, True, True)
        ball_roll_rot = hou.FloatParmTemplate('L_ball_roll_rot', 'L Ball Roll Rotate', 1, [0], 0, 10, True, True)
        heel_roll_rot = hou.FloatParmTemplate('L_heel_roll_rot', 'L Heel Roll Rotate', 1, [0], -10, 10, True, True)
        heel_twist_rot = hou.FloatParmTemplate('L_heel_twist_rot', 'L Heel Twist Rotate', 1, [0], -10, 10, True, True)
        outer_roll_rot = hou.FloatParmTemplate('L_outer_roll_rot', 'L Outer Roll Rotate', 1, [0], -10, 10, True, True)
        inner_roll_rot = hou.FloatParmTemplate('L_inner_roll_rot', 'L Inner Roll Rotate', 1, [0], -10, 10, True, True)
        ##add the floats to the folders
        foot_folder.addParmTemplate(toe_roll_rot)
        foot_folder.addParmTemplate(toe_twist_rot)
        foot_folder.addParmTemplate(ball_roll_rot)
        foot_folder.addParmTemplate(heel_roll_rot)
        foot_folder.addParmTemplate(heel_twist_rot)
        foot_folder.addParmTemplate(outer_roll_rot)
        foot_folder.addParmTemplate(inner_roll_rot)
        
        ##add hand folder to arm folder
        leg_folder.addParmTemplate(foot_folder)
        ##add the spine folder to the template group
        rig_ptg.addParmTemplate(leg_folder)
        ##reset the rig_net template back to the copy we have been editing
        rig_net.setParmTemplateGroup(rig_ptg)
        
        ####LEG UI IMPLEMENTATION####
        leg_kin.parm('blend').setExpression('ch("../../L_leg_FK_IK")')
        leg_goal.parm('tx').setExpression('ch("../L_leg_IK_transx")')
        leg_goal.parm('ty').setExpression('ch("../L_leg_IK_transy")')
        leg_goal.parm('tz').setExpression('ch("../L_leg_IK_transz")')
        leg_goal.parm('rx').setExpression('ch("../L_leg_IK_rotx")')
        leg_goal.parm('ry').setExpression('ch("../L_leg_IK_roty")')
        leg_goal.parm('rz').setExpression('ch("../L_leg_IK_rotz")')
        leg_twist.parm('tx').setExpression('ch("../L_leg_twist_transx")')
        leg_twist.parm('ty').setExpression('ch("../L_leg_twist_transy")')
        leg_twist.parm('tz').setExpression('ch("../L_leg_twist_transz")')
        leg_ctrl1.parm('rx').setExpression('ch("../L_leg_bone1_FK_rotx")')
        leg_ctrl1.parm('ry').setExpression('ch("../L_leg_bone1_FK_roty")')
        leg_ctrl1.parm('rz').setExpression('ch("../L_leg_bone1_FK_rotz")')
        leg_ctrl2.parm('rx').setExpression('ch("../L_leg_bone2_FK_rotx")')
        leg_ctrl2.parm('ry').setExpression('ch("../L_leg_bone2_FK_roty")')
        leg_ctrl2.parm('rz').setExpression('ch("../L_leg_bone2_FK_rotz")')
        foot_ctrl.parm('rx').setExpression('ch("../L_foot_FK_rotx")')
        foot_ctrl.parm('ry').setExpression('ch("../L_foot_FK_roty")')
        foot_ctrl.parm('rz').setExpression('ch("../L_foot_FK_rotz")')
        toe_ctrl.parm('rx').setExpression('ch("../L_toe_FK_rotx")')
        toe_ctrl.parm('ry').setExpression('ch("../L_toe_FK_roty")')
        toe_ctrl.parm('rz').setExpression('ch("../L_toe_FK_rotz")')
        toe_roll.parm('rx').setExpression('ch("../L_toe_roll_rot")*6')
        toe_roll.parm('ry').setExpression('ch("../L_toe_twist_rot")*6')
        ball_roll.parm('rx').setExpression('ch("../L_ball_roll_rot")*6')
        heel_roll.parm('rx').setExpression('ch("../L_heel_roll_rot")*6')
        heel_roll.parm('ry').setExpression('ch("../L_heel_twist_rot")*6')
        outer_roll.parm('rz').setExpression('ch("../L_outer_roll_rot")*6')
        inner_roll.parm('rz').setExpression('ch("../L_inner_roll_rot")*6')
        ##display
        leg_bone1.parm('tdisplay').set(True)
        leg_bone2.parm('tdisplay').set(True)
        foot_bone1.parm('tdisplay').set(True)
        foot_bone2.parm('tdisplay').set(True)
        leg_goal.parm('tdisplay').set(True)
        leg_twist.parm('tdisplay').set(True)
        leg_ctrl1.parm('tdisplay').set(True)
        leg_ctrl2.parm('tdisplay').set(True)
        foot_ctrl.parm('tdisplay').set(True)
        toe_ctrl.parm('tdisplay').set(True)
        leg_bone1.parm('display').setExpression('if (ch("../L_leg_bone_display") == 1 && ch("../m_bone_display") == 1, 1, 0)')
        leg_bone2.parm('display').setExpression('if (ch("../L_leg_bone_display") == 1 && ch("../m_bone_display") == 1, 1, 0)')
        foot_bone1.parm('display').setExpression('if (ch("../L_leg_bone_display") == 1 && ch("../m_bone_display") == 1, 1, 0)')
        foot_bone2.parm('display').setExpression('if (ch("../L_leg_bone_display") == 1 && ch("../m_bone_display") == 1, 1, 0)')
        leg_goal.parm('display').setExpression('if (ch("../L_leg_ctrl_display") == 1 && ch("../m_ctrl_display") == 1 && ch("../L_leg_FK_IK") == 1, 1, 0)')
        leg_twist.parm('display').setExpression('if (ch("../L_leg_ctrl_display") == 1 && ch("../m_ctrl_display") == 1 && ch("../L_leg_FK_IK") == 1, 1, 0)')
        leg_ctrl1.parm('display').setExpression('if (ch("../L_leg_ctrl_display") == 1 && ch("../m_ctrl_display") == 1 && ch("../L_leg_FK_IK") == 0, 1, 0)')
        leg_ctrl2.parm('display').setExpression('if (ch("../L_leg_ctrl_display") == 1 && ch("../m_ctrl_display") == 1 && ch("../L_leg_FK_IK") == 0, 1, 0)')
        foot_ctrl.parm('display').setExpression('if (ch("../L_leg_ctrl_display") == 1 && ch("../m_ctrl_display") == 1 && ch("../L_leg_FK_IK") == 0, 1, 0)')
        toe_ctrl.parm('display').setExpression('if (ch("../L_leg_ctrl_display") == 1 && ch("../m_ctrl_display") == 1 && ch("../L_leg_FK_IK") == 0, 1, 0)')
        
        
        ##NOTE TO SELF: USE THIS AFTER CREATING ALL THE CONTROLS AND CONSTRAINTS FOR THE PURPOSE OF MIRRORING
        ##create an L_side list
        L_side = []
        ##for every node that has 'L_' in their name, add it to the L_side list
        for child in rig_net.children():
            ##pass through any name that has 'L_' in it
            ##the is not -1 means it will only pass through names that match because names that don't will have a value of -1
            if child.name().find('L_') is not -1:
                    L_side.append(child)
        
        
        rig_net.layoutChildren()
        
def run():
    ##check to see if the QT widget already exists
    for ui_item in hou.qt.mainWindow().children():
        
        if type(ui_item).__name__ == 'RigCreatorUI':
            
            ui_item.close()
            ui_item.setParent(None)
            
    RigCreatorUI()