#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import math
import sys
from pathlib import Path
import numpy as np

import gmsh
from gmshairfoil2d.airfoil_func import (NACA_4_digit_geom, get_airfoil_points,
                                        get_all_available_airfoil_names)
from gmshairfoil2d.geometry_def import (AirfoilSpline, Circle, PlaneSurface,
                                        Rectangle, CurveLoop, outofbounds, CType)


def main():
    # Instantiate the parser
    parser = argparse.ArgumentParser(
        description="Optional argument description",
        usage=argparse.SUPPRESS,
        formatter_class=lambda prog: argparse.HelpFormatter(
            prog, max_help_position=80, width=99
        ),
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="Display all airfoil available in the database : https://m-selig.ae.illinois.edu/ads/coord_database.html",
    )

    parser.add_argument(
        "--naca",
        type=str,
        metavar="4DIGITS",
        nargs="?",
        help="NACA airfoil 4 digit",
    )

    parser.add_argument(
        "--airfoil",
        type=str,
        metavar="NAME",
        nargs="?",
        help="Name of an airfoil profile in the database (database available with the --list argument)",
    )

    parser.add_argument(
        "--aoa",
        type=float,
        nargs="?",
        help="Angle of attack [deg] (default: 0 [deg])",
        default=0.0,
    )

    parser.add_argument(
        "--farfield",
        type=float,
        metavar="RADIUS",
        nargs="?",
        default=10,
        help="Create a circular farfield mesh of given radius [m] (default 10m)",
    )
    parser.add_argument(
        "--box",
        type=str,
        metavar="LENGTHxWIDTH",
        nargs="?",
        help="Create a box mesh of dimensions [length]x[height] [m]",
    )
    parser.add_argument(
        "--airfoil_mesh_size",
        type=float,
        metavar="SIZE",
        nargs="?",
        default=0.01,
        help="Mesh size of the airfoil contour [m]  (default 0.01m)",
    )

    parser.add_argument(
        "--ext_mesh_size",
        type=float,
        metavar="SIZE",
        nargs="?",
        default=0.2,
        help="Mesh size of the external domain [m] (default 0.2m) (for normal, bl and structural)",
    )

    parser.add_argument(
        "--no_bl",
        action="store_true",
        help="Do the unstructured meshing (with triangles), without a boundary layer",
    )

    parser.add_argument(
        "--first_layer",
        type=float,
        metavar="HEIGHT",
        nargs="?",
        default=3e-5,
        help="Height of the first layer [m] (default 3e-5m) (for bl and structural)",
    )

    parser.add_argument(
        "--ratio",
        type=float,
        metavar="RATIO",
        nargs="?",
        default=1.2,
        help="Growth ratio of layers (default 1.2) (for bl and structural)",
    )

    parser.add_argument(
        "--nb_layers",
        type=int,
        metavar="INT",
        nargs="?",
        default=35,
        help="Total number of layers in the boundary layer (default 35)",
    )

    parser.add_argument(
        "--format",
        type=str,
        nargs="?",
        default="su2",
        help="Format of the mesh file, e.g: msh, vtk, wrl, stl, mesh, cgns, su2, dat (default su2)",
    )

    parser.add_argument(
        "--structural",
        action="store_true",
        help="Generate a structural mesh",
    )
    parser.add_argument(
        "--arg_struc",
        type=str,
        metavar="[LxLxL]",
        default="1x10x10",
        help="Parameters for the structural mesh [leading (axis x)]x[wake (axis x)]x[total height (axis y)] [m] (default 1x10x10)",
    )

    parser.add_argument(
        "--output",
        type=str,
        metavar="PATH",
        nargs="?",
        default=".",
        help="Output path for the mesh file (default : current dir)",
    )

    parser.add_argument(
        "--ui",
        action="store_true",
        help="Open GMSH user interface to see the mesh",
    )
    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit()

    if args.list:
        get_all_available_airfoil_names()
        sys.exit()

    # Airfoil choice
    cloud_points = None
    if args.naca:
        airfoil_name = args.naca
        cloud_points = NACA_4_digit_geom(airfoil_name)

    if args.airfoil:
        airfoil_name = args.airfoil
        cloud_points = get_airfoil_points(airfoil_name)

    if cloud_points is None:
        print("\nNo airfoil profile specified, exiting")
        print("You must use --naca or --airfoil\n")
        parser.print_help()
        sys.exit()

    # Make the points all start by the (0,0) (or minimum of coord x when not exactly 0) to be easier to deal with after
    le = min(p[0] for p in cloud_points)
    for p in cloud_points:
        if p[0] == le:
            debut = cloud_points.index(p)
    cloud_points = cloud_points[debut:]+cloud_points[:debut]

    # Points need to go clockwise (and still start with 0)
    if cloud_points[1][1] < cloud_points[0][1]:
        cloud_points.reverse()
        cloud_points = cloud_points[-1:] + cloud_points[:-1]

    # Angle of attack
    aoa = -args.aoa * (math.pi / 180)

    # Generate Geometry
    gmsh.initialize()

    # Airfoil
    airfoil = AirfoilSpline(
        cloud_points, args.airfoil_mesh_size, args.structural)
    airfoil.rotation(aoa, (0.5, 0, 0), (0, 0, 1))
    airfoil.gen_skin()
    gmsh.model.geo.synchronize()

    if args.structural:
        dx_lead, dx_wake, dy = [float(value)
                                for value in args.arg_struc.split("x")]
        ext_domain = CType(airfoil, dx_lead, dx_wake, dy,
                           args.ext_mesh_size, args.first_layer, args.ratio)
    else:
        # Create a boundary layer
        # Choose the parameters
        N = args.nb_layers
        r = args.ratio
        d = [args.first_layer]
        # Construct the vector of cumulative distance of each layer from airfoil
        for i in range(1, N):
            d.append(d[-1] - (-d[0]) * r**i)

        # Need to check that the layers do not go outside the box/circle (d[-1] is the total height of bl)
        outofbounds(airfoil, args.box, args.farfield, d[-1])

        # External domain
        if args.box:
            length, width = [float(value) for value in args.box.split("x")]
            ext_domain = Rectangle(0.5, 0, 0, length, width,
                                   mesh_size=args.ext_mesh_size)
        else:
            ext_domain = Circle(0.5, 0, 0, radius=args.farfield,
                                mesh_size=args.ext_mesh_size)
        gmsh.model.geo.synchronize()

        # Create the surface for the triangular mesh
        surface = PlaneSurface([ext_domain, airfoil])
        gmsh.model.geo.synchronize()

        if not args.no_bl:
            curv = [airfoil.upper_spline.tag,  airfoil.lower_spline.tag]

            # Creates a new mesh field of type 'BoundaryLayer' and assigns it an ID (f).
            f = gmsh.model.mesh.field.add('BoundaryLayer')

            # Add the curves where we apply the boundary layer (around the airfoil for us)
            gmsh.model.mesh.field.setNumbers(f, 'CurvesList', curv)
            gmsh.model.mesh.field.setNumber(f, 'Size', d[0])  # size 1st layer
            gmsh.model.mesh.field.setNumber(f, 'Ratio', r)  # Growth ratio

            # Forces to use quads and not triangle when =1 (i.e. true)
            gmsh.model.mesh.field.setNumber(f, 'Quads', 1)

            # Total thickness of boundary layer (instead of nb of layer as before)
            gmsh.model.mesh.field.setNumber(f, 'Thickness', d[-1])
            gmsh.model.mesh.field.setNumbers(
                f, "FanPointsList", [airfoil.te.tag])

            gmsh.model.mesh.field.setAsBoundaryLayer(f)

        # Define boundary conditions (name the curves)
        ext_domain.define_bc()
        surface.define_bc()
        airfoil.define_bc()

    gmsh.model.geo.synchronize()

    # Generate mesh
    gmsh.option.setNumber("Mesh.BoundaryLayerFanElements", 15)
    gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 1)
    gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
    gmsh.model.mesh.generate(2)
    gmsh.model.mesh.optimize("Laplace2D", 5)

    # Open user interface of GMSH
    if args.ui:
        gmsh.fltk.run()

    # Mesh file name and output
    mesh_path = Path(
        args.output, f"mesh_airfoil_{airfoil_name}.{args.format}")
    gmsh.write(str(mesh_path))
    gmsh.finalize()


if __name__ == "__main__":
    main()
