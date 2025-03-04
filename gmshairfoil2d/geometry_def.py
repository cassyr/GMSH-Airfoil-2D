"""
This script contain the definition of geometrical objects needed to build the geometry.
"""

from operator import attrgetter
import gmsh
import numpy as np
import math


class Point:
    """
    A class to represent the point geometrical object of gmsh

    ...

    Attributes
    ----------
    x : float
        position in x
    y : float
        position in y
    z : float
        position in z
    mesh_size : float
        If mesh_size is > 0, add a meshing constraint
            at that point
    """

    def __init__(self, x, y, z, mesh_size):

        self.x = x
        self.y = y
        self.z = z
        self.mesh_size = mesh_size
        self.dim = 0

        # create the gmsh object and store the tag of the geometric object
        self.tag = gmsh.model.geo.addPoint(
            self.x, self.y, self.z, self.mesh_size)

    def rotation(self, angle, origin, axis):
        """
        Method to rotate the object Point
        ...

        Parameters
        ----------
        angle : float
            angle of rotation in rad
        origin : tuple
            tuple of point (x,y,z) which is the origin of the rotation
        axis : tuple
            tuple of point (x,y,z) which represent the axis of rotation
        """
        gmsh.model.geo.rotate(
            [(self.dim, self.tag)],
            *origin,
            *axis,
            angle,
        )

    def translation(self, vector):
        """
        Method to translate the object Point
        ...

        Parameters
        ----------
        direction : tuple
            tuple of point (x,y,z) which represent the direction of the translation
        """
        gmsh.model.geo.translate([(self.dim, self.tag)], *vector)


class Line:
    """
    A class to represent the Line geometrical object of gmsh

    ...

    Attributes
    ----------
    start_point : Point
        first point of the line
    end_point : Point
        second point of the line
    """

    def __init__(self, start_point, end_point):
        self.start_point = start_point
        self.end_point = end_point

        self.dim = 1

        # create the gmsh object and store the tag of the geometric object
        self.tag = gmsh.model.geo.addLine(
            self.start_point.tag, self.end_point.tag)

    def rotation(self, angle, origin, axis):
        """
        Method to rotate the object Line
        ...

        Parameters
        ----------
        angle : float
            angle of rotation in rad
        origin : tuple
            tuple of point (x,y,z) which is the origin of the rotation
        axis : tuple
            tuple of point (x,y,z) which represent the axis of rotation
        """
        gmsh.model.geo.rotate(
            [(self.dim, self.tag)],
            *origin,
            *axis,
            angle,
        )

    def translation(self, vector):
        """
        Method to translate the object Line
        ...

        Parameters
        ----------
        direction : tuple
            tuple of point (x,y,z) which represent the direction of the translation
        """
        gmsh.model.geo.translate([(self.dim, self.tag)], *vector)


class Spline:
    """
    A class to represent the Spine geometrical object of gmsh

    ...

    Attributes
    ----------
    points_list : list(Point)
        list of Point object forming the Spline
    """

    def __init__(self, point_list):
        self.point_list = point_list

        # generate the Lines tag list to follow
        self.tag_list = [point.tag for point in self.point_list]
        self.dim = 1
        # create the gmsh object and store the tag of the geometric object
        self.tag = gmsh.model.geo.addSpline(self.tag_list)

    def rotation(self, angle, origin, axis):
        """
        Method to rotate the object Spline

        Rotate the spline itself (curve, startpoint,endpoint), then rotate the intermediate points
        ...

        Parameters
        ----------
        angle : float
            angle of rotation in rad
        origin : tuple
            tuple of point (x,y,z) which is the origin of the rotation
        axis : tuple
            tuple of point (x,y,z) which represent the axis of rotation
        """
        gmsh.model.geo.rotate(
            [(self.dim, self.tag)],
            *origin,
            *axis,
            angle,
        )

        [
            interm_point.rotation(angle, origin, axis)
            for interm_point in self.point_list[1:-1]
        ]

    def translation(self, vector):
        """
        Method to translate the object Line

        Translate the spline itself (curve, starpoint,endpoint), then translate the indermediate points
        ...

        Parameters
        ----------
        direction : tuple
            tuple of point (x,y,z) which represent the direction of the translation
        """
        gmsh.model.geo.translate([(self.dim, self.tag)], *vector)
        [interm_point.translation(vector)
         for interm_point in self.point_list[1:-1]]


class CurveLoop:
    """
    A class to represent the CurveLoop geometrical object of gmsh
    Curveloop object are an addition entity of the existing line that forms it
    Curveloop must be created when the geometry is in its final layout

    ...

    Attributes
    ----------
    line_list : list(Line)
        List of Line object, in the order of the wanted CurveLoop and closed
        Possibility to give either the tags directly, or the object Line
    """

    def __init__(self, line_list):

        self.line_list = line_list
        self.dim = 1
        # generate the Lines tag list to follow
        # first we check if given the tags directly (and not the object Line)
        if len(line_list) == 0 or isinstance(line_list[0], int):
            self.tag_list = line_list
        else:
            self.tag_list = [line.tag for line in self.line_list]
        # create the gmsh object and store the tag of the geometric object
        self.tag = gmsh.model.geo.addCurveLoop(self.tag_list)

    def close_loop(self):
        """
        Method to form a close loop with the current geometrical object. In our case, we already have it so just return the tag

        Returns
        -------
        _ : int
            return the tag of the CurveLoop object
        """
        return self.tag

    def define_bc(self):
        """
        Method that define the marker of the CurveLoop (when used as boundary layer boundary)
        for the boundary condition
        -------
        """

        self.bc = gmsh.model.addPhysicalGroup(self.dim, [self.tag])
        self.physical_name = gmsh.model.setPhysicalName(
            self.dim, self.bc, "top of boundary layer")


class CircleArc:
    """
    A class to represent a CircleArc geometrical object (a arccirle of angle less than pi)

    ...

    Attributes
    ----------
    xc : float
        position of the center in x
    yc : float
        position of the center in y
    z : float
        position in z
    startpoint : Point
        starting point of the arccircle
    endpoint : Point
        ending point of the arccircle
    mesh_size : float
        determine the mesh resolution and how many segment the
        resulting circle will be composed of
    """

    def __init__(self, xc, yc, zc, start, end, mesh_size):
        # Position of the disk center
        self.xc = xc
        self.yc = yc
        self.zc = zc

        self.startpoint = start
        self.endpoint = end
        self.mesh_size = mesh_size
        self.dim = 1

        center = Point(self.xc, self.yc, self.zc, self.mesh_size)
        self.tag = gmsh.model.geo.addCircleArc(
            self.startpoint.tag, center.tag, self.endpoint.tag)

    def close_loop(self):
        """
        Method to form a close loop with the current geometrical object

        Returns
        -------
        _ : int
            return the tag of the CurveLoop object
        """
        return gmsh.model.geo.addCurveLoop(self.arcCircle_list)

    def define_bc(self):
        """
        Method that define the marker of the circle
        for the boundary condition
        -------
        """

        self.bc = gmsh.model.addPhysicalGroup(self.dim, self.arcCircle_list)
        self.physical_name = gmsh.model.setPhysicalName(
            self.dim, self.bc, "farfield")


class Circle:
    """
    A class to represent a Circle geometrical object, composed of many arcCircle object of gmsh

    ...

    Attributes
    ----------
    xc : float
        position of the center in x
    yc : float
        position of the center in y
    z : float
        position in z
    radius : float
        radius of the circle
    mesh_size : float
        determine the mesh resolution and how many segment the
        resulting circle will be composed of
    """

    def __init__(self, xc, yc, zc, radius, mesh_size):
        # Position of the disk center
        self.xc = xc
        self.yc = yc
        self.zc = zc

        self.radius = radius
        self.mesh_size = mesh_size
        self.dim = 1

        # create a structured arcCircle to merge in one curveloop
        # first compute how many points on the circle
        self.distribution = math.floor(
            (np.pi * 2 * self.radius) / self.mesh_size)
        realmeshsize = (np.pi * 2 * self.radius)/self.distribution
        # don't need the meshsize on the center one, so whatever
        center = Point(self.xc, self.yc, self.zc, realmeshsize)
        # create all the points for the circle
        points = []
        for i in range(0, self.distribution):
            angle = 2 * np.pi / self.distribution * i
            p = Point(self.xc+self.radius*math.cos(angle), self.yc+self.radius *
                      math.sin(angle), self.zc, realmeshsize)
            points.append(p)
        points.append(points[0])
        print(self.distribution, (np.pi * 2 * self.radius)/self.distribution)
        # create arcs between two neighbouring points to create circle
        self.arcCircle_list = [
            gmsh.model.geo.addCircleArc(
                points[i].tag,
                center.tag,
                points[i+1].tag,
            )
            for i in range(0, self.distribution)
        ]
        # Remove the duplicated points generated by the arcCircle
        gmsh.model.geo.synchronize()
        gmsh.model.geo.removeAllDuplicates()

    def close_loop(self):
        """
        Method to form a close loop with the current geometrical object

        Returns
        -------
        _ : int
            return the tag of the CurveLoop object
        """
        return gmsh.model.geo.addCurveLoop(self.arcCircle_list)

    def define_bc(self):
        """
        Method that define the marker of the circle
        for the boundary condition
        -------
        """

        self.bc = gmsh.model.addPhysicalGroup(self.dim, self.arcCircle_list)
        self.physical_name = gmsh.model.setPhysicalName(
            self.dim, self.bc, "farfield")

    def rotation(self, angle, origin, axis):
        """
        Method to rotate the object Circle
        ...

        Parameters
        ----------
        angle : float
            angle of rotation in rad
        origin : tuple
            tuple of point (x,y,z) which is the origin of the rotation
        axis : tuple
            tuple of point (x,y,z) which represent the axis of rotation
        """
        [
            gmsh.model.geo.rotate(
                [(self.dim, arccircle)],
                *origin,
                *axis,
                angle,
            )
            for arccircle in self.arcCircle_list
        ]

    def translation(self, vector):
        """
        Method to translate the object Circle
        ...

        Parameters
        ----------
        direction : tuple
            tuple of point (x,y,z) which represent the direction of the translation
        """
        [
            gmsh.model.geo.translate([(self.dim, arccircle)], *vector)
            for arccircle in self.arcCircle_list
        ]


class Rectangle:
    """
    A class to represent a rectangle geometrical object, composed of 4 Lines object of gmsh

    ...

    Attributes
    ----------
    xc : float
        position of the center in x
    yc : float
        position of the center in y
    z : float
        position in z
    dx: float
        length of the rectangle along the x direction
    dy: float
        length of the rectangle along the y direction
    mesh_size : float
        attribute given for the class Point
    """

    def __init__(self, xc, yc, z, dx, dy, mesh_size):

        self.xc = xc
        self.yc = yc
        self.z = z

        self.dx = dx
        self.dy = dy

        self.mesh_size = mesh_size
        self.dim = 1
        # Generate the 4 corners of the rectangle
        self.points = [
            Point(self.xc - self.dx / 2, self.yc -
                  self.dy / 2, z, self.mesh_size),
            Point(self.xc + self.dx / 2, self.yc -
                  self.dy / 2, z, self.mesh_size),
            Point(self.xc + self.dx / 2, self.yc +
                  self.dy / 2, z, self.mesh_size),
            Point(self.xc - self.dx / 2, self.yc +
                  self.dy / 2, z, self.mesh_size),
        ]
        gmsh.model.geo.synchronize()

        # Generate the 4 lines of the rectangle
        self.lines = [
            Line(self.points[0], self.points[1]),
            Line(self.points[1], self.points[2]),
            Line(self.points[2], self.points[3]),
            Line(self.points[3], self.points[0]),
        ]

        gmsh.model.geo.synchronize()

    def close_loop(self):
        """
        Method to form a close loop with the current geometrical object

        Returns
        -------
        _ : int
            return the tag of the CurveLoop object
        """
        return CurveLoop(self.lines).tag

    def define_bc(self):
        """
        Method that define the different markers of the rectangle for the boundary condition
        self.lines[0] => wall_bot
        self.lines[1] => outlet
        self.lines[2] => wall_top
        self.lines[3] => inlet
        -------
        """

        self.bc_in = gmsh.model.addPhysicalGroup(
            self.dim, [self.lines[3].tag], tag=-1)
        gmsh.model.setPhysicalName(self.dim, self.bc_in, "inlet")

        self.bc_out = gmsh.model.addPhysicalGroup(
            self.dim, [self.lines[1].tag])
        gmsh.model.setPhysicalName(self.dim, self.bc_out, "outlet")

        self.bc_wall = gmsh.model.addPhysicalGroup(
            self.dim, [self.lines[0].tag, self.lines[2].tag]
        )
        gmsh.model.setPhysicalName(self.dim, self.bc_wall, "wall")

        self.bc = [self.bc_in, self.bc_out, self.bc_wall]

    def rotation(self, angle, origin, axis):
        """
        Method to rotate the object Rectangle
        ...

        Parameters
        ----------
        angle : float
            angle of rotation in rad
        origin : tuple
            tuple of point (x,y,z) which is the origin of the rotation
        axis : tuple
            tuple of point (x,y,z) which represent the axis of rotation
        """
        [line.rotation(angle, origin, axis) for line in self.lines]

    def translation(self, vector):
        """
        Method to translate the object Rectangle
        ...

        Parameters
        ----------
        direction : tuple
            tuple of point (x,y,z) which represent the direction of the translation
        """
        [line.translation(vector) for line in self.lines]


class Airfoil:
    """
    A class to represent and airfoil as a CurveLoop object formed with lines

    ...

    Attributes
    ----------
    point_cloud : list(list(float))
        List of points forming the airfoil in the order,
        each point is a list containing in the order
        its position x,y,z
    mesh_size : float
        attribute given for the class Point,Note that a mesh size larger
        than the resolution given by the cloud of points
        will not be taken into account
    name : str
        name of the marker that will be associated to the airfoil
        boundary condition
    """

    def __init__(self, point_cloud, mesh_size, name="airfoil"):

        self.name = name
        self.dim = 1
        # Generate Points object from the point_cloud
        self.points = [
            Point(point_cord[0], point_cord[1], point_cord[2], mesh_size)
            for point_cord in point_cloud
        ]

    def gen_skin(self):
        """
        Method to generate the line forming the foil, Only call this function when the points
        of the airfoil are in their final position
        -------
        """
        self.lines = [
            Line(self.points[i], self.points[i + 1])
            for i in range(-1, len(self.points) - 1)
        ]
        self.lines_tag = [line.tag for line in self.lines]

    def close_loop(self):
        """
        Method to form a close loop with the current geometrical object

        Returns
        -------
        _ : int
            return the tag of the CurveLoop object
        """
        return CurveLoop(self.lines).tag

    def define_bc(self):
        """
        Method that define the marker of the airfoil for the boundary condition
        -------
        """

        self.bc = gmsh.model.addPhysicalGroup(self.dim, self.lines_tag)
        gmsh.model.setPhysicalName(self.dim, self.bc, self.name)

    def rotation(self, angle, origin, axis):
        """
        Methode to rotate the object CurveLoop
        ...

        Parameters
        ----------
        angle : float
            angle of rotation in rad
        origin : tuple
            tuple of point (x,y,z) which is the origin of the rotation
        axis : tuple
            tuple of point (x,y,z) which represent the axis of rotation
        """
        [point.rotation(angle, origin, axis) for point in self.points]

    def translation(self, vector):
        """
        Method to translate the object CurveLoop
        ...

        Parameters
        ----------
        direction : tuple
            tuple of point (x,y,z) which represent the direction of the translation
        """
        [point.translation(vector) for point in self.points]


class AirfoilSpline:
    """
    A class to represent and airfoil as a CurveLoop object formed with Splines
    ...

    Attributes
    ----------
    point_cloud : list(list(float))
        List of points forming the airfoil in the order,
        each point is a list containing in the order
        its position x,y,z
    mesh_size : float
        attribute given for the class Point,Note that a mesh size larger
        than the resolution given by the cloud of points
        will not be taken into account
    cut_te: bool
        attribute given to hold true when we want a cute trailing edge, instead of a pointy one
    name : str
        name of the marker that will be associated to the airfoil
        boundary condition
    """

    def __init__(self, point_cloud, mesh_size, cut_te, name="airfoil"):

        self.name = name
        self.dim = 1
        self.cut_te = cut_te
        # Generate Points object from the point_cloud
        self.points = [
            Point(point_cord[0], point_cord[1], point_cord[2], mesh_size)
            for point_cord in point_cloud
        ]
        # Find leading and trailing edge location
        # in space
        self.le = min(self.points, key=attrgetter("x"))
        self.te = max(self.points, key=attrgetter("x"))
        # in the list of point
        self.te_indx = self.points.index(self.te)
        self.le_indx = self.points.index(self.le)
        if cut_te:
            if self.points[self.te_indx-1].x == 1:
                if self.points[self.te_indx-1].y > self.points[self.te_indx].y:
                    self.te_up_indx = self.te_indx-1
                    self.te_down_indx = self.te_indx
                else:
                    self.te_up_indx = self.te_indx
                    self.te_down_indx = self.te_indx-1
            elif (self.te_indx != len(self.points) and self.points[self.te_indx+1].x == 1):
                if self.points[self.te_indx+1].y > self.points[self.te_indx].y:
                    self.te_up_indx = self.te_indx+1
                    self.te_down_indx = self.te_indx
                else:
                    self.te_up_indx = self.te_indx
                    self.te_down_indx = self.te_indx+1
            elif (self.te_indx == len(self.points) and self.points[0].x == 1):
                if self.points[0].y > self.points[self.te_indx].y:
                    self.te_up_indx = 0
                    self.te_down_indx = self.te_indx
                else:
                    self.te_up_indx = self.te_indx
                    self.te_down_indx = 0
            else:
                self.points.pop(self.te_indx)
                te1 = self.points[self.te_indx-1]
                if self.te_indx == len(self.points):
                    te2 = self.points[0]
                else:
                    te2 = self.points[self.te_indx]
                if te1.y < te2.y:
                    self.te_down = te1
                    self.te_up = te2
                else:
                    self.te_down = te2
                    self.te_up = te1
                self.te_down_indx = self.points.index(self.te_down)
                self.te_up_indx = self.points.index(self.te_up)

    def gen_skin(self):
        """
        Method to generate the two splines forming the foil, Only call this function when the points
        of the airfoil are in their final position
        -------
        """
        # Create the Splines depending on the le and te location in point_cloud
        if self.cut_te:
            if self.le_indx < self.te_up_indx:
                # create a spline from the leading edge to the trailing edge
                self.upper_spline = Spline(
                    self.points[self.le_indx: self.te_up_indx + 1])
                # create a spline from the trailing edge to the leading edge
                if self.te_down_indx < self.le_indx:
                    # in this case we have te_down_index=0, as te_down_index is always one behind te_up_index
                    self.lower_spline = Spline(
                        self.points[: (self.le_indx) + 1]
                    )
                else:
                    self.lower_spline = Spline(
                        self.points[self.te_down_indx:] +
                        self.points[: (self.le_indx) + 1]
                    )
            else:
                # create a spline from the leading edge to the trailing edge
                self.upper_spline = Spline(
                    self.points[self.le_indx:] +
                    self.points[: (self.te_up_indx + 1)]
                )
                # create a spline from the trailing edge to the leading edge
                self.lower_spline = Spline(
                    self.points[self.te_down_indx: self.le_indx + 1])
            x1 = self.points[self.te_up_indx].x
            x2 = self.points[self.te_down_indx].x
            y1 = self.points[self.te_up_indx].y
            y2 = self.points[self.te_down_indx].y
            distance = math.sqrt((x1-x2)*(x1-x2)+(y1-y2)*(y1-y2))
            print(x1, x2, y1, y2, "and", (x1+x2) /
                  2, (x1+x2)/2+distance/2*(y2-y1))
            self.te_line = CircleArc(
                (x1+x2)/2+(y2-y1)/3, (y1+y2)/2+(x1-x2)/3, 0,
                self.points[self.te_up_indx], self.points[self.te_down_indx], self.points[0].mesh_size)
            gmsh.model.geo.mesh.setTransfiniteCurve(self.te_line.tag, 10)
            return self.upper_spline, self.lower_spline, self.te_line
        else:
            if self.le_indx < self.te_indx:
                # create a spline from the leading edge to the trailing edge
                self.upper_spline = Spline(
                    self.points[self.le_indx: self.te_indx + 1])
                # create a spline from the trailing edge to the leading edge
                self.lower_spline = Spline(
                    self.points[self.te_indx:] +
                    self.points[: (self.le_indx) + 1]
                )

            else:
                # create a spline from the leading edge to the trailing edge
                self.upper_spline = Spline(
                    self.points[self.le_indx:] +
                    self.points[: (self.te_indx + 1)]
                )
                # create a spline from the trailing edge to the leading edge
                self.lower_spline = Spline(
                    self.points[self.te_indx: self.le_indx + 1])
            return self.upper_spline, self.lower_spline
        # form the curvedloop

    def close_loop(self):
        """
        Method to form a close loop with the current geometrical object

        Returns
        -------
        _ : int
            return the tag of the CurveLoop object
        """
        if self.cut_te:
            return CurveLoop([self.upper_spline, self.te_line, self.lower_spline]).tag
        else:
            return CurveLoop([self.upper_spline, self.lower_spline]).tag

    def define_bc(self):
        """
        Method that define the marker of the airfoil for the boundary condition
        -------
        """

        self.bc = gmsh.model.addPhysicalGroup(
            self.dim, [self.upper_spline.tag, self.lower_spline.tag]
        )
        gmsh.model.setPhysicalName(self.dim, self.bc, self.name)

    def rotation(self, angle, origin, axis):
        """
        Method to rotate the object AirfoilSpline
        ...

        Parameters
        ----------
        angle : float
            angle of rotation in rad
        origin : tuple
            tuple of point (x,y,z) which is the origin of the rotation
        axis : tuple
            tuple of point (x,y,z) which represent the axis of rotation
        """
        [point.rotation(angle, origin, axis) for point in self.points]

    def translation(self, vector):
        """
        Method to translate the object AirfoilSpline
        ...

        Parameters
        ----------
        direction : tuple
            tuple of point (x,y,z) which represent the direction of the translation
        """
        [point.translation(vector) for point in self.points]


class PlaneSurface:
    """
    A class to represent the PlaneSurface geometrical object of gmsh


    ...

    Attributes
    ----------
    geom_objects : list(geom_object)
        List of geometrical object able to form closedloop,
        First the object will be closed in ClosedLoop
        the first curve loop defines the exterior contour; additional curve loop
        define holes in the surface domaine

    """

    def __init__(self, geom_objects):

        self.geom_objects = geom_objects
        # close_loop() will form a close loop object and return its tag
        self.tag_list = [geom_object.close_loop()
                         for geom_object in self.geom_objects]
        self.dim = 2

        # create the gmsh object and store the tag of the geometric object
        self.tag = gmsh.model.geo.addPlaneSurface(self.tag_list)

    def define_bc(self):
        """
        Method that define the domain marker of the surface
        -------
        """
        self.ps = gmsh.model.addPhysicalGroup(self.dim, [self.tag])
        gmsh.model.setPhysicalName(self.dim, self.ps, "fluid")
