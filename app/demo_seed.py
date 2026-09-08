from dataclasses import dataclass

from app.asset.services import validate_rack_placement
from app.extensions import db
from app.models import (
    Asset,
    AssetStatus,
    AssetType,
    Datacenter,
    DatacenterStatus,
    Rack,
    RackStatus,
    Room,
    RoomStatus,
    VirtualMachine,
    VirtualMachineEnvironment,
    VirtualMachineStatus,
)
from app.virtual_machine.services import get_valid_host


DATACENTERS = (
    {
        "key": "principal",
        "name": "Datacenter Principal",
        "code": "DC-MCZ-01",
        "location": "Maceió - AL (ambiente fictício)",
        "description": "Datacenter principal de demonstração do InfraManager.",
        "status": DatacenterStatus.ACTIVE.value,
    },
    {
        "key": "secondary",
        "name": "Datacenter Secundário",
        "code": "DC-MCZ-02",
        "location": "Maceió - AL (ambiente fictício)",
        "description": "Datacenter secundário de demonstração do InfraManager.",
        "status": DatacenterStatus.ACTIVE.value,
    },
)

ROOMS = (
    {
        "key": "production",
        "datacenter": "principal",
        "name": "Sala Produção",
        "code": "PROD",
        "description": "Sala fictícia para cargas de produção.",
        "status": RoomStatus.ACTIVE.value,
    },
    {
        "key": "staging",
        "datacenter": "principal",
        "name": "Sala Homologação",
        "code": "HML",
        "description": "Sala fictícia para cargas de homologação.",
        "status": RoomStatus.ACTIVE.value,
    },
    {
        "key": "recovery",
        "datacenter": "secondary",
        "name": "Sala Disaster Recovery",
        "code": "DR",
        "description": "Sala fictícia para continuidade e recuperação.",
        "status": RoomStatus.ACTIVE.value,
    },
)

RACKS = (
    ("prod-a01", "production", "Rack Produção A01", "A01", 42),
    ("prod-a02", "production", "Rack Produção A02", "A02", 42),
    ("prod-a03", "production", "Rack Produção A03", "A03", 42),
    ("hml-h01", "staging", "Rack Homologação H01", "H01", 42),
    ("dr-dr01", "recovery", "Rack Disaster Recovery DR01", "DR01", 44),
)

ASSETS = (
    (
        "SRV-PROD-01",
        "prod-a01",
        "Servidor Produção 01",
        AssetType.SERVER,
        1,
        2,
        AssetStatus.ACTIVE,
    ),
    (
        "SRV-PROD-02",
        "prod-a01",
        "Servidor Produção 02",
        AssetType.SERVER,
        3,
        2,
        AssetStatus.ACTIVE,
    ),
    (
        "STORAGE-01",
        "prod-a02",
        "Storage Principal",
        AssetType.STORAGE,
        1,
        4,
        AssetStatus.INACTIVE,
    ),
    (
        "SW-CORE-01",
        "prod-a02",
        "Switch Core 01",
        AssetType.SWITCH,
        41,
        1,
        AssetStatus.ACTIVE,
    ),
    (
        "SW-CORE-02",
        "prod-a03",
        "Switch Core 02",
        AssetType.SWITCH,
        41,
        1,
        AssetStatus.MAINTENANCE,
    ),
    (
        "SRV-HML-01",
        "hml-h01",
        "Servidor Homologação 01",
        AssetType.SERVER,
        1,
        2,
        AssetStatus.ACTIVE,
    ),
    (
        "SRV-DR-01",
        "dr-dr01",
        "Servidor Disaster Recovery 01",
        AssetType.SERVER,
        1,
        2,
        AssetStatus.ACTIVE,
    ),
)

VIRTUAL_MACHINES = (
    (
        "vm-web-01",
        "SRV-PROD-01",
        "10.10.10.11",
        2,
        4096,
        80,
        VirtualMachineEnvironment.PRODUCTION,
        VirtualMachineStatus.RUNNING,
    ),
    (
        "vm-web-02",
        "SRV-PROD-02",
        "10.10.10.12",
        2,
        4096,
        80,
        VirtualMachineEnvironment.PRODUCTION,
        VirtualMachineStatus.RUNNING,
    ),
    (
        "vm-db-01",
        "SRV-PROD-01",
        "10.10.20.10",
        4,
        8192,
        200,
        VirtualMachineEnvironment.PRODUCTION,
        VirtualMachineStatus.RUNNING,
    ),
    (
        "vm-monitoramento",
        "SRV-PROD-02",
        "10.10.20.20",
        2,
        4096,
        100,
        VirtualMachineEnvironment.PRODUCTION,
        VirtualMachineStatus.MAINTENANCE,
    ),
    (
        "vm-homologacao",
        "SRV-HML-01",
        "10.20.10.10",
        2,
        4096,
        80,
        VirtualMachineEnvironment.STAGING,
        VirtualMachineStatus.STOPPED,
    ),
    (
        "vm-backup",
        "SRV-DR-01",
        "10.30.10.10",
        4,
        8192,
        500,
        VirtualMachineEnvironment.PRODUCTION,
        VirtualMachineStatus.SUSPENDED,
    ),
    (
        "vm-ad-01",
        "SRV-DR-01",
        "10.30.10.11",
        2,
        4096,
        100,
        VirtualMachineEnvironment.PRODUCTION,
        VirtualMachineStatus.RUNNING,
    ),
)


class DemoSeedConflictError(ValueError):
    pass


@dataclass
class DemoSeedResult:
    created: int = 0
    existing: int = 0


def seed_demo_data() -> DemoSeedResult:
    result = DemoSeedResult()
    datacenters: dict[str, Datacenter] = {}
    rooms: dict[str, Room] = {}
    racks: dict[str, Rack] = {}
    assets: dict[str, Asset] = {}

    for values in DATACENTERS:
        datacenter = db.session.scalar(
            db.select(Datacenter).where(Datacenter.code == values["code"])
        )
        if datacenter is None:
            datacenter = Datacenter(
                name=values["name"],
                code=values["code"],
                location=values["location"],
                description=values["description"],
                status=values["status"],
            )
            db.session.add(datacenter)
            db.session.flush()
            result.created += 1
        else:
            result.existing += 1
        datacenters[values["key"]] = datacenter

    for values in ROOMS:
        datacenter = datacenters[values["datacenter"]]
        room = db.session.scalar(
            db.select(Room).where(
                Room.datacenter_id == datacenter.id,
                Room.code == values["code"],
            )
        )
        if room is None:
            room = Room(
                datacenter=datacenter,
                name=values["name"],
                code=values["code"],
                description=values["description"],
                status=values["status"],
            )
            db.session.add(room)
            db.session.flush()
            result.created += 1
        else:
            result.existing += 1
        rooms[values["key"]] = room

    for key, room_key, name, code, capacity_u in RACKS:
        room = rooms[room_key]
        rack = db.session.scalar(
            db.select(Rack).where(Rack.room_id == room.id, Rack.code == code)
        )
        if rack is None:
            rack = Rack(
                room=room,
                name=name,
                code=code,
                capacity_u=capacity_u,
                description="Rack fictício para demonstração do InfraManager.",
                status=RackStatus.ACTIVE.value,
            )
            db.session.add(rack)
            db.session.flush()
            result.created += 1
        else:
            result.existing += 1
        racks[key] = rack

    for index, values in enumerate(ASSETS, start=1):
        asset_tag, rack_key, name, asset_type, position, units, status = values
        rack = racks[rack_key]
        asset = db.session.scalar(db.select(Asset).where(Asset.asset_tag == asset_tag))
        if asset is None:
            validate_rack_placement(rack, position, units)
            asset = Asset(
                rack=rack,
                name=name,
                asset_tag=asset_tag,
                serial_number=f"SN-DEMO-{index:03d}",
                manufacturer="Fabricante Demo",
                model="Modelo Demo",
                asset_type=asset_type.value,
                rack_unit_start=position,
                rack_units=units,
                description="Ativo fictício para demonstração do InfraManager.",
                status=status.value,
            )
            db.session.add(asset)
            db.session.flush()
            result.created += 1
        else:
            if (
                asset.rack_id != rack.id
                or asset.asset_type != asset_type.value
                or asset.rack_unit_start != position
                or asset.rack_units != units
            ):
                raise DemoSeedConflictError(
                    "Existing demo asset conflicts with the expected topology."
                )
            result.existing += 1
        assets[asset_tag] = asset

    for values in VIRTUAL_MACHINES:
        name, host_tag, ip, vcpu, memory, disk, environment, status = values
        host = get_valid_host(assets[host_tag].id)
        virtual_machine = db.session.scalar(
            db.select(VirtualMachine).where(VirtualMachine.name == name)
        )
        if virtual_machine is None:
            virtual_machine = VirtualMachine(
                host_asset=host,
                name=name,
                hostname=f"{name}.example.test",
                ip_address=ip,
                operating_system="Ubuntu Server 24.04 LTS",
                vcpu=vcpu,
                memory_mb=memory,
                disk_gb=disk,
                environment=environment.value,
                status=status.value,
                description="Máquina virtual fictícia para demonstração.",
            )
            db.session.add(virtual_machine)
            db.session.flush()
            result.created += 1
        else:
            if virtual_machine.host_asset_id != host.id:
                raise DemoSeedConflictError(
                    "Existing demo virtual machine conflicts with the expected host."
                )
            result.existing += 1

    db.session.commit()
    return result
